#!/usr/bin/python

import struct
import random
import gant

class AntFsWorkflow(gant.Workflow):

        """
        Serial Number uniquely identifying this ANTFS host.
        """
        HOST_SN = random.randint(0x0000, 0xFFFF)

        class Link(gant.Workflow):

                """
                Each time an ANTFS connection LINK is started a random frequency should be selected
                from this list. If an ANTFS connection is lost, we'll transition back to LINK, and
                pick a new frequency. Actuall frequency = 2400 + n, e.g. 3 = 2403mhz.
                """
                FREQUENCY_AGILITY = [3, 7, 15, 20, 25, 29, 34, 40, 45, 49, 54, 60, 65, 70, 75, 80]

                """
                The requested becon period when sending an ANTFS LINK. 0b100 (8hz) is provides
                least latency before burst/ack messages can be sent, but is most harsh on battery.
                Period = 2^(n-1), for 0 <= n <= 4. Other values Reserved
                """
                BEACON_PERIOD = 4

                def enter(self, ctx):
                        """
                        Invoked when ANT ANTFS beacon changes to LINK.
                        """
                        self.freq = random.choice(self.FREQUENCY_AGILITY)
                        self.period = self.BEACON_PERIOD
                        super(AntFsWorkflow.Link, self).enter(ctx)

                class SendLink(workflow.WaitForAcknowledgedOrBurst):

                        def enter(self, ctx):
                                link_msg = struct.pack("<BBI", ctx.workflow.freq, ctx.workflow.period, AntFsWorkflow.HOST_SN)

                        



# vim: et ts=8 sts=8
