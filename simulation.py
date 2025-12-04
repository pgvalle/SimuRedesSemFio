from ns import ns
import csv
import scipy.stats as sci
import numpy as np

SEED = 1
ROUNDS = 10
DURATION = 60

TCPS = ['NewReno', 'Vegas', 'Veno', 'WestwoodPlus']
BERS = [1e-6, 1e-5, 1e-4, 1e-3]
DELAYS = ['1ms', '10ms', '20ms', '50ms']

cpp = ns.cppyy
cpp.cppdef('''
        using namespace ns3;

        template<typename... Args>
        Callback<void, Args...> MakeMyCallback(void(*function)(Args...))
        {
            return MakeCallback(function);
        }
           ''')

def ConfidenceOffset(samples, confidence=0.95):
    alpha = 1 - confidence
    quantile = 1 - alpha / 2

    n = len(samples)
    t = sci.t.ppf(quantile, df=n-1)
    offset = t * np.std(samples, ddof=1) / np.sqrt(n)

    return offset


def Main():
    ns.RngSeedManager.SetSeed(SEED)

    entries = [['tcp', 'ber', 'delay', 'mean', 'off99', 'off95']]

    for tcp in TCPS:
        ns.Config.SetDefault('ns3::TcpL4Protocol::SocketType',
                             ns.StringValue('ns3::Tcp' + tcp))

        for delay in DELAYS:
            for ber in BERS:
                print(f'params: tcp={tcp}, delay={delay}, ber={ber}')

                throughputs = []
                for i in range(1, ROUNDS + 1):
                    print(f' {i}', end='', flush=True)
                    ns.RngSeedManager.SetRun(i)
                    throughput = Simulate(ber, delay)
                    throughputs.append(throughput)

                mean = np.mean(throughputs)
                off99 = ConfidenceOffset(throughputs, confidence=0.99)
                off95 = ConfidenceOffset(throughputs, confidence=0.95)
                entries.append([tcp, ber, delay, mean, off99, off95])
                print(f' mean: {mean}, off99: {off99}, off95 {off95}')

    with open('results.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(entries)


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

    # wifi with no signal loss
    wifiChannel = ns.YansWifiChannelHelper()
    wifiChannel.SetPropagationDelay('ns3::ConstantSpeedPropagationDelayModel')
    wifiChannel.AddPropagationLoss('ns3::FixedRssLossModel', 'Rss', ns.DoubleValue(0.0))

    # artificial ber on phy layer
    errorModel = ns.CreateObject[ns.RateErrorModel]()
    errorModel.SetRate(ber)
    errorModel.SetUnit(ns.RateErrorModel.ERROR_UNIT_BIT)

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

    # ethernet nodes
    csmaNodes = ns.NodeContainer()
    csmaNodes.Add(ap)
    csmaNodes.Add(server)
    # ethernet
    csma = ns.CsmaHelper()
    csma.SetChannelAttribute('DataRate', ns.StringValue('100Mbps'))
    csma.SetChannelAttribute('Delay', ns.TimeValue(ns.Time(delay)))
    # ethernet nics
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

    # server ip address with port
    serverIp = csmaInterfaces.GetAddress(1)
    dest = ns.InetSocketAddress(serverIp, port=5000).ConvertTo()
    # sink application on server
    sink = ns.PacketSinkHelper('ns3::TcpSocketFactory', dest)
    sinkApp = sink.Install(server)
    # bulk application on ap
    bulk = ns.BulkSendHelper('ns3::TcpSocketFactory', dest)
    bulk.SetAttribute('SendSize', ns.UintegerValue(1400))
    bulkApp = bulk.Install(sta)

    global timeFirstTx, timeLastRx
    timeFirstTx = ns.Time(0)
    timeLastRx = ns.Time(0)

    def TxCallback(pkt: ns.Packet) -> None:
        global timeFirstTx
        if timeFirstTx == ns.Time(0):
            timeFirstTx = ns.Simulator.Now()

    def RxCallback(pkt: ns.Packet, addr: ns.Address) -> None:
        global timeLastRx
        timeLastRx = ns.Simulator.Now()

    ns.Config.ConnectWithoutContext('/NodeList/*/ApplicationList/*/$ns3::BulkSendApplication/Tx',
                                    cpp.gbl.MakeMyCallback['ns3::Ptr<const ns3::Packet>'](TxCallback))
    ns.Config.ConnectWithoutContext('/NodeList/*/ApplicationList/*/$ns3::PacketSink/Rx',
                                    cpp.gbl.MakeMyCallback['ns3::Ptr<const ns3::Packet>', 'const ns3::Address&'](RxCallback))

    sinkApp.Start(ns.Seconds(0))
    bulkApp.Start(ns.Seconds(1))

    ns.Simulator.Stop(ns.Seconds(DURATION + 1))
    ns.Simulator.Run()

    rx = sinkApp.Get(0).GetTotalRx()
    delta = (timeLastRx - timeFirstTx).GetSeconds()
    throughput = 8e-3 * (rx / delta) if delta > 0 else 0

    ns.Simulator.Destroy()
    return throughput


Main()
