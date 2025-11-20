from ns import ns
import sys
import ctypes
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as sst

PORT = 5000
STARTTIME = 0.0
ENDTIME = 60.0
SEED = 54294301
RUNS = 10
CONFIDENCE = 95

wifiPhyDrops = 0
wifiMacDrops = 0

def WifiPhyDropCallback(packet: ns.Packet, snr: ctypes.c_double) -> None:
    global wifiPhyDrops
    wifiPhyDrops += 1

def WifiMacDropCallback(packet: ns.Packet) -> None:
    global wifiMacDrops
    wifiMacDrops += 1

cpp = ns.cppyy
cpp.cppdef("""
    using namespace ns3;

    Ptr<RateErrorModel> MakeRateErrorModel(double rate) {
        Ptr<RateErrorModel> model = CreateObject<RateErrorModel>();
        model->SetRate(rate);
        model->SetUnit(RateErrorModel::ERROR_UNIT_BIT);
        return model;
    }

    Callback<void, Ptr<const Packet>, double>
    MakeWifiPhyDropCallback(void(*func)(Ptr<const Packet>, double)) {
        return MakeCallback(func);
    }

    Callback<void, Ptr<const Packet>>
    MakeWifiMacDropCallback(void(*func)(Ptr<const Packet>)) {
        return MakeCallback(func);
    }
                """)


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
    dest = ns.InetSocketAddress(serverIp, PORT).ConvertTo()

    sink = ns.PacketSinkHelper("ns3::TcpSocketFactory", dest)
    sinkApp = sink.Install(server)

    bulk = ns.BulkSendHelper("ns3::TcpSocketFactory", dest)
    bulkApp = bulk.Install(sta)

    ns.Config.ConnectWithoutContext("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/State/RxError", 
                                    cpp.gbl.MakeWifiPhyDropCallback(WifiPhyDropCallback))
    ns.Config.ConnectWithoutContext("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Mac/MacRxDrop", 
                                    cpp.gbl.MakeWifiMacDropCallback(WifiMacDropCallback))

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


buf = ctypes.create_string_buffer(b"NewReno", 32)
c_tcp = ctypes.c_char_p(buf.raw)
c_ber = ctypes.c_double(0)

cmd = ns.CommandLine(__file__)
cmd.AddValue("tcp", "TCP variant", c_tcp, 32)
cmd.AddValue("ber", "Bit-error rate", c_ber)
cmd.Parse(sys.argv)

ns.RngSeedManager.SetSeed(SEED)
ns.Config.SetDefault("ns3::TcpL4Protocol::SocketType", 
                     ns.StringValue("ns3::Tcp" + c_tcp.value.decode()))

throughputs = []

for i in range(RUNS):
    ns.RngSeedManager.SetRun(i)
    wifiPhyDrops = 0
    wifiMacDrops = 0

    print(f"Run {i + 1} started... ", end="", flush=True)
    throughput = Simulate(c_ber.value)
    throughputs.append(throughput)
    print(f"Done!\nthroughput: {throughput:.3f}Kbps")

a = 1 - CONFIDENCE / 100
q = 1 - a / 2
t = sst.t.ppf(q, df=RUNS - 1)

mean = np.mean(throughputs)
err = np.std(throughputs, ddof=1) / np.sqrt(RUNS)
off = t * err / np.sqrt(RUNS)

print(f"mean={mean}; a={a}; t={t}")
print("throughputs:")
for throughput in throughputs:
    print(throughput)

