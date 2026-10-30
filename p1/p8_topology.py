
from mininet.topo import Topo

class IoTWANTopo(Topo):
    def build(self, n=20):
        n = int(n)

        # 1. Gateway switches
        g1 = self.addSwitch('g1', dpid='0000000000000001')
        g2 = self.addSwitch('g2', dpid='0000000000000002')

        # 2. 6 WAN switches
        w1 = self.addSwitch('w1', dpid='0000000000000003')
        w2 = self.addSwitch('w2', dpid='0000000000000004')
        w3 = self.addSwitch('w3', dpid='0000000000000005')
        w4 = self.addSwitch('w4', dpid='0000000000000006')
        w5 = self.addSwitch('w5', dpid='0000000000000007')
        w6 = self.addSwitch('w6', dpid='0000000000000008')

        # 3.IoT hosts
        for i in range(1, n + 1):

            # Site 1: h1 ... h20
            h1 = self.addHost(
                f'h{i}',
                ip=f'10.0.0.{i}/24'
            )
            self.addLink(h1, g1)

            # Site 2: h21 ... h40
            j = n + i
            h2 = self.addHost(
                f'h{j}',
                ip=f'10.0.0.{j}/24'
            )
            self.addLink(h2, g2)

        # 4. Data Centers
        dcA = self.addHost(
            'dca',
            ip='10.0.0.241/24'
        )
        dcB = self.addHost(
            'dcb',
            ip='10.0.0.242/24'
        )

        # 5. Gateway -> WAN
        self.addLink(g1, w1, delay='10ms')
        self.addLink(g2, w1, delay='10ms')

        # 6. Primary route to DC A
        # w1 -> w2 -> w3 -> w6
        self.addLink(w1, w2, delay='10ms')
        self.addLink(w2, w3, delay='10ms')
        self.addLink(w3, w6, delay='10ms')

        # 7. Backup route to  DC A
        # w1 -> w4 -> w6
        self.addLink(w1, w4, delay='10ms')
        self.addLink(w4, w6, delay='10ms')

        # 8. Route to DC B
        # w1 -> w5
        self.addLink(w1, w5, delay='10ms')

        # 9. Connect the  Data Centers
        self.addLink(w6, dcA, delay='10ms')
        self.addLink(w5, dcB, delay='10ms')

# Load the topology in  Mininet
topos = {
    'iotwan': (lambda n=20: IoTWANTopo(n=n))
}
