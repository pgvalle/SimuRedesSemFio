from ns import ns
import csv
import utils

utils.printEnabled = True

SEED = 1
ROUNDS = 20
DURATION = 60

TCPS = ['NewReno', 'Vegas', 'Veno', 'WestwoodPlus']
BERS = [1e-6, 1e-5, 1e-4, 1e-3]
DELAYS = ['1ms', '10ms', '20ms', '50ms']

cpp = ns.cppyy
cpp.cppdef('''
           using namespace ns3;

           Ptr<RateErrorModel> MakeRateErrorModel(double ber) {
               Ptr<RateErrorModel> model = CreateObject<RateErrorModel>();
               model->SetRate(ber);
               model->SetUnit(RateErrorModel::ERROR_UNIT_BIT);
               return model;
           }
           ''')

ns.RngSeedManager.SetSeed(SEED)

def main():
    entries = [['tcp', 'ber', 'delay', 'mean', 'off']]

    for tcp in TCPS:
        ns.Config.SetDefault('ns3::TcpL4Protocol::SocketType',
                             ns.StringValue('ns3::Tcp' + tcp))

        for ber in BERS:
            for delay in DELAYS:
                utils.myprint(f'runing for tcp={tcp}, ber={ber}, delay={delay}')
                utils.printEnabled = False

                throughputs = []
                for i in range(1, ROUNDS + 1):
                    utils.myprint(f' round {i:02d} out of {ROUNDS}... ')

                    ns.RngSeedManager.SetRun(i)

                    throughput = Simulate(ber, delay)
                    throughputs.append(throughput)
                    utils.myprint(f'  result: {throughput}')

                mean, off = utils.interval(throughputs, confidence=0.99)
                entries.append([tcp, ber, delay, mean, off])

                utils.printEnabled = True
                utils.myprint(f' mean: {mean}, off: {off}')

    with open('results-99.csv', 'a+', newline='') as file:
        writer = csv.writer(file)

        if file.tell() == 0: # only write headers if file was empty
            writer.writerow(entries[0])
        writer.writerows(entries[1:])


def Simulate(ber, delay):
    # nodes
    nodes = ns.NodeContainer()
    nodes.Create(3)
    sta = nodes.Get(0)
    ap = nodes.Get(1)
    server = nodes.Get(2)

    # all nodes are static
    mobility = ns.MobilityHelper()
    mobility.SetMobilityModel('ns3::ConstantPositionMobilityModel')
    mobility.Install(nodes)

    # wifi phy layer with no signal loss
    wifiChannel = ns.YansWifiChannelHelper()
    wifiChannel.SetPropagationDelay('ns3::ConstantSpeedPropagationDelayModel')
    wifiChannel.AddPropagationLoss('ns3::FixedRssLossModel', 'Rss', ns.DoubleValue(0.0))
    # put artificial ber on phy layer
    errorModel = cpp.gbl.MakeRateErrorModel(ber)
    wifiPhy = ns.YansWifiPhyHelper()
    wifiPhy.SetChannel(wifiChannel.Create())
    wifiPhy.SetErrorRateModel('ns3::YansErrorRateModel')
    wifiPhy.Set('PostReceptionErrorModel', ns.PointerValue(errorModel))

    wifi = ns.WifiHelper()
    wifi.SetStandard(ns.WIFI_STANDARD_80211ac)
    wifiMac = ns.WifiMacHelper()

    # station nic
    wifiMac.SetType('ns3::StaWifiMac')
    staDev = wifi.Install(wifiPhy, wifiMac, sta)
    # ap nic
    wifiMac.SetType('ns3::ApWifiMac')
    apDev = wifi.Install(wifiPhy, wifiMac, ap)
    # all wifi nics
    wifiDevs = ns.NetDeviceContainer()
    wifiDevs.Add(staDev)
    wifiDevs.Add(apDev)

    # ethernet
    csmaNodes = ns.NodeContainer()
    csmaNodes.Add(ap)
    csmaNodes.Add(server)
    # ethernet nics
    csma = ns.CsmaHelper()
    csma.SetChannelAttribute('DataRate', ns.StringValue('100Mbps'))
    csma.SetChannelAttribute('Delay', ns.TimeValue(ns.Time(delay)))
    csmaDevs = csma.Install(csmaNodes)

    addr = ns.Ipv4AddressHelper()
    stack = ns.InternetStackHelper()
    stack.Install(nodes)
    # put an ip on the wifi nics
    addr.SetBase('10.1.1.0', '255.255.255.0')
    wifiInterfaces = addr.Assign(wifiDevs)
    # put an ip on the ethernet nics
    addr.SetBase('10.1.2.0', '255.255.255.0')
    csmaInterfaces = addr.Assign(csmaDevs)

    ns.Ipv4GlobalRoutingHelper.PopulateRoutingTables()

    serverIp = csmaInterfaces.GetAddress(1)
    dest = ns.InetSocketAddress(serverIp, port=5000).ConvertTo()

    sink = ns.PacketSinkHelper('ns3::TcpSocketFactory', dest)
    sinkApp = sink.Install(server)

    bulk = ns.BulkSendHelper('ns3::TcpSocketFactory', dest)
    bulkApp = bulk.Install(sta)

    monitorHelper = ns.FlowMonitorHelper()
    monitor = monitorHelper.InstallAll()

    monitor.Start(ns.Seconds(0))
    sinkApp.Start(ns.Seconds(0))
    bulkApp.Start(ns.Seconds(1))

    ns.Simulator.Stop(ns.Seconds(DURATION + 1))
    ns.Simulator.Run()

    stats = monitor.GetFlowStats()
    throughput = 0
    for flowId, flow in stats:
        time = flow.timeLastRxPacket - flow.timeFirstTxPacket
        throughput = 8e-3 * (flow.rxBytes / time.GetSeconds())
        break

    ns.Simulator.Destroy()
    return throughput


main()
