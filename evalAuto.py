# -*- coding: utf-8 -*-

from matplotlib import pyplot as plt
import os

class Case():
    def __init__(self):
        # Optical sets
        self.OptSets = {
                1: 'CFK for Flappanels, Green PCB for Sidepanels',
                2: 'White Coating on SC Side of Flappanels, White Coating on Sidepanels',
                3: 'White Coating on Flappanels + Sidepanels',
                4: 'Special low alpha/epsilon coating'
                }
        # Power budget
        self.powBud = {
                0: 'No heat load/Extreme Cold',
                1: 'Nominal Orbit w\o Contact',
                2: 'Nominal Orbit w\ good COM Contact (min UHF/VHF)',
                3: 'Nominal Orbit w\ medium Contact',
                4: 'S-Band (4min, 8min UHF/VHF)',
                5: 'PL Measurement',
                6: 'THM Hot Case (20min COM contact)',
                7: 'Safe Mode w\o UHF/VHF Contact',
                8: 'Orbit with 10 min UHF/VHF and S-Band contact'
                }
        # Orientation
        self.orient = {
                1: 'Zenith Pointing',
                2: 'Sun Pointing',
                3: 'Random Tumbling'
                }

        self.checkComb()

    def checkComb(self):
        for i in self.OptSets:
            for j in self.powBud:
                for k in self.orient:
                    self.caseComb = str(i) + str(j) + str(k)
                    self.path = 'MOVE_II_3_' + str(self.caseComb)[0] + '/esatan/Case_' + self.caseComb
                    if os.path.isdir(self.path):
                        self.fetchTemp()
                        self.saveExtrema()
                    else:
                        pass

    def fetchTemp(self):
        filePath = self.path + '/MOVE_II_.out'
        print 'Reading temperature data from ESATAN logfile {}'.format(filePath)

        with open(filePath) as logFile:
                lines = logFile.readlines()
        
        timestep = 0
        self.data = {}
        self.components = []
        for i,line in enumerate(lines):
                # Search for temperature data paragraph
                if '+MOVE' in line:
                        timestep += 1
                        
                        # This if is necessary because in some files the data following the +MOVE flag is not temperature data
                        if lines[i+3].split()[2] == 'T':
                            for l in lines[i+6:]:               #skip subheader
                                # Break at end of paragraph
                                if not l.strip():
                                        break
                                else:
                                        lWords = l.split()
                                        component = lWords[1]
                                        try:
                                            temp = float(lWords[2])
                                        except Exception:
                                            pass

                                        if component not in self.data.keys():
                                            self.components.append(component)
                                            self.data[component] = {}
                                            self.data[component]['Tmax_global'] = (0.0,-9999)
                                            self.data[component]['Tmin_global'] = (0.0,9999)
                                        if timestep not in self.data[component].keys():
                                            self.data[component][timestep] = {}
                                            self.data[component][timestep]['Tmax'] = -9999
                                            self.data[component][timestep]['Tmin'] = 9999 
                                        
                                        # Check against global extrema
                                        if temp > self.data[component]['Tmax_global'][1] and temp != 0.0:
                                            self.data[component]['Tmax_global'] = (timestep,temp)
                                        elif temp < self.data[component]['Tmin_global'][1] and temp != 0.0:
                                            self.data[component]['Tmin_global'] = (timestep,temp)

                                        # Determine extrema for this timestep
                                        if temp > self.data[component][timestep]['Tmax'] and temp!= 0.0:
                                            self.data[component][timestep]['Tmax'] = temp
                                        elif temp < self.data[component][timestep]['Tmin'] and temp != 0.0:
                                            self.data[component][timestep]['Tmin'] = temp
    

    def saveExtrema(self):
        if not os.path.isdir('autoExtremaLogs'): os.mkdir('autoExtremaLogs')
        saveFile = 'autoExtremaLogs/extrema_' + self.caseComb + '.txt'
        print "Writing data to file", saveFile
        f = open(saveFile,'w')

        f.write('Component\tTmax\tTmin\n')

        for comp in self.data.keys():
                string = '{:60s}{:15s}{:15s}\n'.format(comp, str(self.data[comp]['Tmax_global'][1]), str(self.data[comp]['Tmin_global'][1]))
                f.write(string)

        f.close()
        
obj = Case()
