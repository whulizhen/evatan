# -*- coding: utf-8 -*-

from matplotlib import pyplot as plt
import os
import numpy as np

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

        self.promptCase()
	self.checkComb()
	self.fetchTemp()

    def promptCase(self):
        
	for key in self.OptSets.keys():
	    	print '{}: {}'.format(key,self.OptSets[key])
	print ''
	for key in self.powBud.keys():
	    	print '{}: {}'.format(key,self.powBud[key])
	print ''
	for key in self.orient.keys():
	    	print '{}: {}'.format(key,self.orient[key])
	print ''

        self.caseComb = raw_input('Which case would you like to evaluate? Provide a three-digit combination based on the options above: ')

    def checkComb(self):
	self.path = 'MOVE_II_3_' + str(self.caseComb)[0] + '/Case_' + self.caseComb
	if os.path.isdir(self.path):
		pass
	else:
		print '{} is not a valid path. The case seems to not exists, try another combination.'.format(self.path)	
                exit()

    def fetchTemp(self):
	filePath = self.path + '/esatan/MOVE_II_.out'
	print 'Reading temperature data from ESATAN logfile {}'.format(filePath)

	with open(filePath) as logFile:
		lines = logFile.readlines()[7:]		#skip header
	
	timestep = 0
	self.data = {}
        self.components = []
	for i,line in enumerate(lines):
		# Search for temperature data paragraph
		if '+MOVE' in line:
			timestep += 1
			for l in lines[i+7:-1]:		#skip subheader as well as first and last data point to eliminate false measurements
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
    
    def plotTemp(self, component):
    	fig = plt.figure()
    	plt.subplot(111)

    	x = []
    	y = []
    	for time in self.data[component].keys():
	    if time not in ('Tmax_global','Tmin_global'):
    		x.append(time)
    		y.append(self.data[component][time]['Tmax'])
    	Tmax_glob = self.data[component]['Tmax_global']
    	Tmin_glob = self.data[component]['Tmin_global']
        
    	plt.plot(x,y, label=component)
    	plt.scatter(Tmax_glob[0],Tmax_glob[1])
    	plt.scatter(Tmin_glob[0],Tmin_glob[1])

	plt.title("Temporal evolution of maximum temperature on part {}".format(component))
	plt.xlabel("Time [timesteps]")
	plt.ylabel("Temperature [C]")
					
        plt.text(5,5,"Global maximum: {} @{}\nGlobal minimum: {} @{}".format(Tmax_glob[1],Tmax_glob[0],Tmin_glob[0],Tmin_glob[1]))
	plt.show()

    def plotExtrema(self):
        fig = plt.figure()
        ax = plt.subplot(111)

        self.components = ['PC104_1','PC104_2']

        x = np.arange(len(self.components))
        yMax = []
        yMin = []
        for comp in self.components:
            yMax.append(self.data[comp]['Tmax_global'][1])
            yMin.append(self.data[comp]['Tmin_global'][1])
        plt.bar(x, yMax, width=0.2, color='b', align='center')
        plt.bar(x+0.2, yMin,width=0.2, color='r', align='center')
        ax.set_xticks(x)

	plt.title("Maximum and minimum temperatures of all components")
	plt.xlabel("Component")
	plt.ylabel("Temperature [C]")
        
        #for i, v in enumerate(yMax):
    	#	ax.text(v + 3, i, str(v), color='blue')
	
        ax.set_xticklabels(self.components)
        plt.xticks(rotation=45)
	plt.show()

    def saveExtrema(self):
	saveFile = 'extrema_' + self.caseComb + '.txt'
	f = open(saveFile,'w')

	f.write('Component\tTmax\tTmin\n')

	for comp in self.data.keys():
		string = comp + ':\t' + str(self.data[comp]['Tmax_global'][1]) + '\t' + str(self.data[comp]['Tmin_global'][1]) + '\n'
		f.write(string)

	f.close()
	
obj = Case()
for comp in obj.components:
	print comp

obj.saveExtrema()
obj.plotExtrema()

while True:
    compToPlot = raw_input('Name component that should be plotted (type exit to end loop): ')
    if compToPlot == 'exit':
        break
    obj.plotTemp(compToPlot)
