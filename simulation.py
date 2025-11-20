from ns import ns
import sys
import ctypes
import csv

SEED = 54294301
RUNS = 10
STARTTIME = 0.0
ENDTIME = 60.0

BUFLEN = 32
tcpArgBuf = ctypes.create_string_buffer(b"NewReno", BUFLEN)
tcpArg = ctypes.c_char_p(tcpArgBuf.raw)
berArg = ctypes.c_double(0)

cmd = ns.CommandLine(__file__)
cmd.AddValue("tcp", "TCP variant", tcpArg, BUFLEN)
cmd.AddValue("ber", "Bit-error rate", berArg)
cmd.Parse(sys.argv)

tcp = tcpArg.value.decode()
ber = berArg.value

ns.RngSeedManager.SetSeed(SEED)
ns.Config.SetDefault("ns3::TcpL4Protocol::SocketType", 
                     ns.StringValue("ns3::Tcp" + tcp))

cpp = ns.cppyy
cpp.cppdef("""
           using namespace ns3;

           Ptr<RateErrorModel> MakeRateErrorModel(double rate) {
               Ptr<RateErrorModel> model = CreateObject<RateErrorModel>();
               model->SetRate(rate);
               model->SetUnit(RateErrorModel::ERROR_UNIT_BIT);
               return model;
           }
           """)


def main():
    duration = ENDTIME - STARTTIME
    filename = f"results/ber-{ber}.txt"

    with open(filename, "a") as f:
        print(SEED, duration, tcp)
        print(SEED, duration, tcp, file=f)

        for i in range(RUNS):
            ns.RngSeedManager.SetRun(i)
            print(f"run {i+1}/{RUNS}")
            throughput = Simulate(ber)
            print(throughput)
            print(throughput, file=f)

        print(file=f)


def Simulate(ber):
    nodes = ns.NodeContainer()
    nodes.Create(3)
    sta = nodes.Get(0)
    ap = nodes.Get(1)
    server = nodes.Get(2)

    mobility = ns.MobilityHelper()
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel")
    mobility.SetPositionAllocator("ns3::GridPositionAllocator")
    mobility.Install(nodes)

    wifiChannel = ns.YansWifiChannelHelper()
    wifiChannel.SetPropagationDelay("ns3::ConstantSpeedPropagationDelayModel")
    wifiChannel.AddPropagationLoss("ns3::FixedRssLossModel", "Rss", ns.DoubleValue(0.0))

    wifiPhy = ns.YansWifiPhyHelper()
    wifiPhy.SetChannel(wifiChannel.Create())
    wifiPhy.SetErrorRateModel("ns3::YansErrorRateModel")

    errorModel = ns.cppyy.gbl.MakeRateErrorModel(ber)
    wifiPhy.Set("PostReceptionErrorModel", ns.PointerValue(errorModel))

    wifi = ns.WifiHelper()
    wifi.SetStandard(ns.WIFI_STANDARD_80211ac)

    ssid = ns.Ssid("pedro")
    wifiMac = ns.WifiMacHelper()

    wifiMac.SetType("ns3::StaWifiMac", "Ssid", ns.SsidValue(ssid))
    staDev = wifi.Install(wifiPhy, wifiMac, sta)

    wifiMac.SetType("ns3::ApWifiMac", "Ssid", ns.SsidValue(ssid))
    apDev = wifi.Install(wifiPhy, wifiMac, ap)

    wifiDevs = ns.NetDeviceContainer()
    wifiDevs.Add(staDev)
    wifiDevs.Add(apDev)

    csmaNodes = ns.NodeContainer()
    csmaNodes.Add(ap)
    csmaNodes.Add(server)

    csma = ns.CsmaHelper()
    csma.SetChannelAttribute("DataRate", ns.StringValue("1Gbps"))
    csma.SetChannelAttribute("Delay", ns.TimeValue(ns.Time("0.5us")))
    csmaDevs = csma.Install(csmaNodes)

    stack = ns.InternetStackHelper()
    stack.Install(nodes)

    addr = ns.Ipv4AddressHelper()

    addr.SetBase("10.1.1.0", "255.255.255.0")
    wifi_ifaces = addr.Assign(wifiDevs)

    addr.SetBase("10.1.2.0", "255.255.255.0")
    csmaInterfaces = addr.Assign(csmaDevs)

    ns.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

    serverIp = csmaInterfaces.GetAddress(1)
    dest = ns.InetSocketAddress(serverIp, port=5000).ConvertTo()

    sink = ns.PacketSinkHelper("ns3::TcpSocketFactory", dest)
    sinkApp = sink.Install(server)

    bulk = ns.BulkSendHelper("ns3::TcpSocketFactory", dest)
    bulkApp = bulk.Install(sta)

    monitorHelper = ns.FlowMonitorHelper()
    monitor = monitorHelper.InstallAll()

    monitor.Start(ns.Seconds(STARTTIME))
    sinkApp.Start(ns.Seconds(STARTTIME))
    bulkApp.Start(ns.Seconds(STARTTIME))
    bulkApp.Stop(ns.Seconds(ENDTIME))

    ns.Simulator.Stop(ns.Seconds(ENDTIME + 5))
    ns.Simulator.Run()
    ns.Simulator.Destroy()

    stats = monitor.GetFlowStats()
    throughput = -1
    for flowId, flow in stats:
        time = (flow.timeLastRxPacket - flow.timeFirstTxPacket).GetSeconds()
        if time > 0:
            throughput = 8e-3 * (flow.rxBytes / time)
        break

    return throughput


main()
