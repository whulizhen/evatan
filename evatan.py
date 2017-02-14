# -*- coding: utf-8 -*-
##########################################
#
# To do:
# - Option to filter nonsensical values
#
##########################################

import logging
logging.basicConfig(filename='eval.log', filemode='a', format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p', level=logging.DEBUG)
logging.info('Program started')
logging.info('Importing matplotlib')
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.pyplot import cm
import matplotlib.patches as mpatches
import matplotlib.transforms as mtransforms

logging.info('Importing PyQt5')
from PyQt5 import QtWidgets
from PyQt5.uic import loadUiType
from PyQt5.QtCore import Qt

logging.info('Importing sys')
import sys
logging.info('Importing os')
import os
logging.info('Importing numpy')
import numpy as np


# Try to find UI file in temp folder created by exe. Works if UI file was included in the exe by tweaking the pyinstaller spec file
if hasattr(sys, '_MEIPASS'):
    ui_path = os.path.join(sys._MEIPASS, "evaltan.ui")
elif hasattr(sys, '_MEIPASS2'):
    ui_path = os.path.join(sys._MEIPASS2, "evatan.ui")
else:
    ui_path = "evatan.ui"

try: 
    Ui_MainWindow, QMainWindow = loadUiType(ui_path)
except Exception:
    logging.critical('GUI file could not be loaded from path {}!'.format(ui_path))
    exit()

class ApplicationWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, ):
        logging.info('Initiating main window')
        super(ApplicationWindow, self).__init__()

        self.fileLoaded = False

        # Create application window
        logging.info("Setting up UI")
        self.setupUi(self)
        self.setWindowTitle('ESATAN Data Evaluation')

        # Load configuration
        self.loadConfig()

        # Case options
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

        # Create string for displaying case options
        caseOptions = ''
        for key in self.OptSets.keys():
            caseOptions += '{}: {}\n'.format(key,self.OptSets[key])
        caseOptions += '\n'
        for key in self.powBud.keys():
            caseOptions += '{}: {}\n'.format(key,self.powBud[key])
        caseOptions += '\n'
        for key in self.orient.keys():
            caseOptions += '{}: {}\n'.format(key,self.orient[key])

        self.caseOptions = caseOptions

        # Set up table for temperature statistics
        self.tempStatTable.setColumnCount(3)
        self.tempStatTable.setColumnCount(3)
        self.tempStatTable.setHorizontalHeaderLabels(['Component','Tmin','Tmax'])
        # Expand columns to fit widget
        self.tempStatTable.horizontalHeader().setStretchLastSection(True)
        

        # Make some menu buttons checkable
        self.menuFixZoom.setCheckable(True)

        # Implement GUI logic
        self.menuFixZoom.toggled.connect(self.updatexPlot)
        self.caseEdit.returnPressed.connect(self.createxPlot)
        self.compSelection.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.compSelection.itemSelectionChanged.connect(self.updatexPlot)
        self.menuViewShowCaseOptions.triggered.connect(self.showCaseOptions)
        self.menuQuit.triggered.connect(self.quit)
        self.menuIgnore.triggered.connect(self.editIgnores)
        self.menuThresholds.triggered.connect(self.editThresholds)
        self.btnLoadFile.clicked.connect(self.loadFile)
        self.menuChangeDir.triggered.connect(self.changeCfg)
        # unbind previous plots from save menu action
        try: 
            self.buttonSaveFig.clicked.disconnect()
        except Exception: 
            pass
        self.buttonSaveFig.clicked.connect(self.savePlot)


    def loadConfig(self):
        """ Loads configuration file 'config.txt'. If it doesn't exist, it is created with the default values. """
        logging.info("Trying to load config file.")
        # If config file doesn't exist, create it with standard values
        if not os.path.isfile('config.txt'):
            logging.info("Config file not found. Creating it with default settings.")
            with open('config.txt', 'w') as f:
                f.write('# Path to the parent folder in which the subfolders with the ESATAN output files reside. Subfolders must be named "Case_<case combination>"\npath = "MOVE_II_3_1/esatan/"\n')
                f.write('# Threshold values above/below which temperatures should be disregarded. Values must be separated by commas.\nthresholds = -200,200\n')
                f.write('# Specific temperature values to be disregarded (For example because they are known to be faulty). Values must be separated by commas.\nignore = 0\n')

        self.parentPath = "MOVE_II_3_1/esatan/"
        self.thresholds = [None, None]
        self.ignoreValues = [0]
        # Load configuration
        with open('config.txt','r') as f:
            logging.info("Reading config file")
            for line in f:
                # Ignore comments
                if not line.startswith('#'):
                    try: 
                        var, val = [str(word).strip().replace('"','').strip() for word in line.split('=')]
                    except:
                        logging.error("Could not read line in configuration file: {}".format(line))
                        continue
                    if var in ('path','Path'):
                        self.parentPath = val
                    elif var in ('thresholds','Thresholds'):
                        try:
                            self.thresholds = [float(v) for v in val.split(',') if v != '']
                        except:
                            logging.error("Could not read threshold values from config file. No filtering will be done.")
                    elif var in ('ignore','Ignore'):
                        try:
                            self.ignoreValues = [float(v) for v in val.split(',')]
                        except:
                            logging.error("Could not read ignore values from config file. No temperature values will be ignored.")
        logging.info("Loaded path to ESATAN files from config file: {}".format(self.parentPath))
        logging.info("Loaded threshold values from config file: {}".format(self.thresholds))
        logging.info("Loaded ignore values from config file: {}".format(self.ignoreValues))


    def showCaseOptions(self):
        """ Opens message box showing case options with descriptions. """
        QtWidgets.QMessageBox.about(self, "Case options", self.caseOptions)


    def loadFile(self):
        """ Loads an ESATAN output file to be searched for temperature data to be evaluated. """
        self.filePath, ok  = QtWidgets.QFileDialog.getOpenFileName(self, caption='Load file', filter='ESATAN output files (*.out)')
        if ok: self.fileLoaded = True

        # Create new canvas and plots
        self.createxPlot()
        

    def quit():
        """ Closes the application """
        self.close()


    def updatexPlot(self):
        # Update plots and draw them
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        self.selectedComps = sorted([str(x.text()) for x in self.compSelection.selectedItems()])
        self.xPlot.fixZoom = self.menuFixZoom.isChecked()
        self.xPlot.updateTemps()
        self.xPlot.updateExtrema()
        self.xPlot.showTempStats()
        self.xPlot.canvas.draw()
        QtWidgets.QApplication.restoreOverrideCursor()


    def createxPlot(self):
        """ Removes old canvas and creates new one when new output file is being loaded. """
        logging.info("Updating plot")
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        # If canvas already exists, delete it
        try:
            self.xPlotLayout.removeWidget(self.xPlotCanvas)
            self.xPlotCanvas.close()
        except:
            logging.warning("plot canvas could not be cleared")
            pass
        
        self.selectedComps = sorted([str(x.text()) for x in self.compSelection.selectedItems()])
        
        # Read case from GUI line input only if file not loaded manually
        if not self.fileLoaded:
            self.caseComb = self.caseEdit.text()
        else: self.caseComb = None

        # Create new plot and canvas
        self.xPlot = Case(self, self.caseComb)
        # If case was not properly set up (e.g. caseComb was incorrect)
        if not hasattr(self.xPlot, 'canvas'):
            return
        self.xPlotCanvas = self.xPlot.canvas
        self.xPlotLayout.addWidget(self.xPlotCanvas)

        # Add margins for xaxis labels
        self.xPlot.fig.subplots_adjust(bottom=0.15)
        
        # Add available components to QList
        self.compSelection.addItems(self.xPlot.components)

        # If no item is selected, select first in list
        if len(self.compSelection.selectedItems()) == 0:
            self.compSelection.setCurrentRow(0)

        # Add Toolbar functionality
        self.toolbar = NavigationToolbar(self.xPlotCanvas, self)
        self.toolbar.hide()
        self.buttonRestore.clicked.connect(self.toolbar.home)
        self.buttonZoom.clicked.connect(self.toolbar.zoom)
        self.buttonPan.clicked.connect(self.toolbar.pan)

        # Unbind previous case from save menu action
        try: 
            self.buttonSaveStats.clicked.disconnect()
        except Exception: 
            pass
        self.buttonSaveStats.clicked.connect(self.saveStats)

        try: 
            self.menuFileSaveAs_2.triggered.disconnect()
        except Exception: 
            pass
        self.menuFileSaveAs_2.triggered.connect(self.savePlot)

        # Enable the user to enter case combinations again
        self.fileLoaded = False

        QtWidgets.QApplication.restoreOverrideCursor()


    def savePlot(self):
        """ Opens save file dialog for saving current plot. """
        fileName, ok = str(QtWidgets.QFileDialog.getSaveFileName(self, 'Save Figure', filter='PNG files (*.png)'))
        if ok:
            if fileName != '': 
                try: 
                    self.xPlot.saveFig(fileName)
                except Exception:
                    logging.error("Could not save figure")
                    pass
            else:
                logging.error("Figure not saved: empty string is not a valid file name")


    def saveStats(self):
        """ Opens save file dialog for saving temperature extrema of all components for current case. """
        fileName = str(QtWidgets.QFileDialog.getSaveFileName(self, 'Save File')[0])
        if fileName != '': 
            try: 
                self.xPlot.saveExtrema(fileName)
            except Exception:
                logging.error("Could not save stats")
                pass
        else:
            logging.error("Extrema not saved: empty string is not a valid file name")


    def editThresholds(self):
        """ Opens dialog with which the user can change certain parts of the config file. """
        newSet = False
        newSetting, ok = QtWidgets.QInputDialog.getText(self, 'Change Threshold Values', 'Values above/below which temperatures should be discarded (comma separated)')

        with open('config.txt', 'r') as f:
            content = f.readlines()

        if ok:
            # Search for affected line and replace it with the new value
            for key, line in enumerate(content):
                if not line.startswith('#') and any(w in line for w in ('thresholds','Thresholds','THRESHOLDS')):
                    content[key] = 'thresholds={}'.format(newSetting)
                    newSet = True
                    break

            # In case the setting didn't exist before, just append it
            if newSet == False:
                content.append('\nthresholds={}'.format(newSetting))

            # Replace file with changed contents
            with open('config.txt', 'w') as f:
                f.writelines(content)

            self.thresholds = newSetting.split(',')
            self.createxPlot()


    def editIgnores(self):
        """ Opens dialog with which the user can change certain parts of the config file. """
        newSet = False
        newSetting, ok = QtWidgets.QInputDialog.getText(self, 'Change Ignore Values', 'Temperature values to ignore (comma separated)')

        with open('config.txt', 'r') as f:
            content = f.readlines()

        if ok:
            # Search for affected line and replace it with the new value
            for key, line in enumerate(content):
                if not line.startswith('#') and any(w in line for w in ('ignore','Ignore','IGNORE')):
                    content[key] = 'ignore={}'.format(newSetting)
                    newSet = True
                    break

            # In case the setting didn't exist before, just append it
            if newSet == False:
                content.append('\nignore={}'.format(newSetting))

            # Replace file with changed contents
            with open('config.txt', 'w') as f:
                f.writelines(content)

            self.ignoreValues = newSetting.split(',')
            self.createxPlot()


    def changeCfg(self):
        """ Opens dialog with which the user can change certain parts of the config file. """
        newSet = False
        newSetting, ok = QtWidgets.QInputDialog.getText(self, 'Change config', 'Path to folder containing ESATAN files (output files have to reside in subfolders named Case_XXX where XXX is the case combination)')

        with open('config.txt', 'r') as f:
            content = f.readlines()

        if ok:
            # Search for affected line and replace it with the new value
            for key, line in enumerate(content):
                if not line.startswith('#') and any(w in line for w in ('path','Path','PATH')):
                    content[key] = 'path={}'.format(newSetting)
                    newSet = True
                    break

            # In case the setting didn't exist before, just append it
            if newSet == False:
                content.append('\npath={}'.format(newSetting))

            # Replace file with changed contents
            with open('config.txt', 'w') as f:
                f.writelines(content)

            self.parentPath = newSetting
            self.createxPlot()


    
class Case():
    """ 
    Class for simulation case. A case is defined by a three-digit case 
    combination specifying the boundary and initial conditions used in the 
    simulation.
    """
    def __init__(self, gui, caseComb=None):
        """ 
        Checks if file was loaded by user or case combination was entered.
        Creates the colormap for the plots. Creates one figure, a canvas, 
        and two axes. Triggers initial plots.
        """
        self.gui = gui
        self.fixZoom = 0
        self.tempMargin = 0.5
        self.plots = {}
        self.extrPlots = {}
        self.caseComb = caseComb
        self.fileLoaded = self.gui.fileLoaded
        self.path = self.gui.parentPath + 'Case_' + str(self.caseComb)
        self.ignoreValues = self.gui.ignoreValues
        self.visiblePlots = []
        self.handles = []
        self.labels = []

        # If thresholds contains a None, sorting will return None
        if self.gui.thresholds.sort() == None:
            self.thresholds = self.gui.thresholds
        else:
            self.thresholds = self.gui.thresholds.sort()

        # If no file has been specified, take caseComb from GUI and search in default folder
        if not self.fileLoaded:
            # On startup, case combination is set to 103
            if self.caseComb == None:
                self.caseComb=103
                self.gui.caseEdit.setText(str(self.caseComb))
            # If case combination is invalid, abort
            if not self.checkComb():
                return
        elif self.fileLoaded:
            self.filePath = self.gui.filePath

        # If data hasn't been read from simulation output file, do that
        try: self.data
        except AttributeError: self.fetchTemp()
        else: pass

        # Create color map with one color for each component
        self.colors= {}
        for color, comp in zip(cm.gist_rainbow(np.linspace(0,1,len(self.data))), self.data.keys()):
            self.colors[comp] = color

        # Create figure and canvas
        self.fig = Figure()
        self.tempAxes = self.fig.add_subplot(121)
        self.extrAxes = self.fig.add_subplot(122)
        self.canvas = FigureCanvas(self.fig)

        # Set figure title based on if case was specified or file was loaded
        if not self.fileLoaded:
            figTitle = "Maximum and minimum temperatures - Case {}".format(self.caseComb)
        else:
            if self .getModel():
                figTitle = "Maximum and minimum temperatures - Model {}".format(self.model)
            else:
                figTitle = "Maximum and minimum temperatures"

        self.fig.suptitle(figTitle)

        self.tempAxes.set_title("Temporal Evolution of Hottest and Coldest Points")
        self.tempAxes.set_xlabel("Time [s]")
        self.tempAxes.set_ylabel("Temperature [$^\circ$C]") 
        
        self.extrAxes.set_title("Absolute Extrema in Time and Space")
        
        self.updateTemps()
        self.updateExtrema()
        
        # Display temperature statistics
        self.showTempStats()


    def getModel(self):
        """ Tries to find the model name for the loaded ESATAN file by searching a line with the word 'submodel' in it. """
        with open(self.filePath) as f:
            for line in f:
                words = line.split()
                if 'submodel' in words:
                    try:
                        self.model = words[ words.index('submodel') + 1 ]
                        return True
                    except IndexError:
                        # Model name could not be found next to flag word
                        return False

        # If no model name could be found, return False
        return False


    def showCombError(self):
        """ Shows error message box if output directory for specified case selection could not be found. """
        msg = QtWidgets.QMessageBox()
        msg.setText('{} is not a valid path or doesn\'t contain an appropriate output file (MOVE_II_.out). The case seems to not exists, try another combination.'.format(self.path))
        msg.setWindowTitle('Unknown case combination')
        msg.exec_()

    
    def checkComb(self):
        """ Checks if output directory and file for specified case selection exist. """
        if os.path.isdir(self.path) and os.path.isfile(self.path + '/MOVE_II_.out'):
            self.filePath = self.path + '/MOVE_II_.out'
            return 1    
        else:
            self.showCombError()
            QtWidgets.QApplication.restoreOverrideCursor()
            return 0


    def fetchTemp(self):
        """ Retrieves temperature data from ESATAN output file. """
        timestep = 0
        self.data = {}
        self.extrema = {}
        self.components = []
        self.time = []
        lowerLim, upperLim = self.thresholds
        logging.info("Ignoring values smaller than {} and higher than {}".format(lowerLim, upperLim))
        
        # This check might not be necessary
        if not os.path.isfile(self.filePath):
            logging.critical("Output file could not be found")
            return

        # Open ESATAN file
        logging.info('Reading temperature data from ESATAN logfile {}'.format(self.filePath))
        with open(self.filePath) as logFile:
            lines = logFile.readlines()    

        # Scan all lines
        for i,line in enumerate(lines):
            # Search for timestamp
            if 'TIMEN' in line:
                time = float(line.split()[2])
                self.time.append(time)

            # Search for temperature data paragraph
            if '+MOVE' in line:
                # This if is necessary because in some files the data following the +MOVE flag is not temperature data
                if lines[i+3].split()[2] == 'T':
                    for l in lines[i+6:]:        #skip subheader
                        # Break at end of paragraph
                        if not l.strip():
                            break
                        else:
                            lWords = l.split()
                            comp = lWords[1]
                            try:
                                temp = float(lWords[2])
                            except Exception:
                                logging.error("Temperature value seems to be faulty: {}".format(lWords[2]))
                                break

                            ## If this temperature doesn't pass a filter, set it to NaN
                            #if upperLim != None and temp > upperLim: 
                            #    logging.info("Filtered too high value {}".format(temp))
                            #    break
                            #    #temp = np.NaN
                            #if lowerLim != None and temp < lowerLim: 
                            #    logging.info("Filtered too low value {}".format(temp))
                            #    break
                            #    #temp = np.NaN
                            #if temp in self.ignoreValues: 
                            #    logging.info("Filtered ignored value")
                            #    break
                            #    #temp = np.NaN

                            # Create new keys if necessary
                            if comp not in self.data.keys():
                                self.components.append(comp)
                                self.data[comp] = {}
                            if comp not in self.extrema.keys():
                                self.extrema[comp] = {}
                                self.extrema[comp]['glob_max'] = (0.0,-9999)
                                self.extrema[comp]['glob_min'] = (0.0,9999)
                            if time not in self.data[comp].keys():
                                self.data[comp][time] = {}
                                self.data[comp][time]['Tmax'] = -9999
                                self.data[comp][time]['Tmin'] = 9999 
                        
                            # See if this temperature is a global extremum
                            if temp > self.extrema[comp]['glob_max'][1]:
                                self.extrema[comp]['glob_max'] = (time,temp)
                            elif temp < self.extrema[comp]['glob_min'][1]:
                                self.extrema[comp]['glob_min'] = (time,temp)

                            # Determine extrema at current time
                            if temp > self.data[comp][time]['Tmax']:
                                self.data[comp][time]['Tmax'] = temp
                            elif temp < self.data[comp][time]['Tmin']:
                                self.data[comp][time]['Tmin'] = temp
                    
        # Check if for all times in array:times there are data points.
        # If filters are activated, that is sometimes not the case.
        # If there are no data points for a certain time, delete it
        print "Cleansing time array"
        print "Time array:\n", self.time
        for comp in self.data.keys():
            print "Data keys:\n", self.data[comp].keys()
            for i, time in enumerate(self.time):
                if time not in self.data[comp].keys():
                    print "Removing time", time
                    self.time.remove(time)
        print self.time
    

    def saveFig(self, fileName):
        """ Uses pyplot savefig function to save the current plot to a file """
        self.fig.savefig(fileName)


    def showTempStats(self):
        """ Shows temperature statistics for selected components. """
        self.selectedComps = sorted([str(x.text()) for x in self.gui.compSelection.selectedItems()])
        table = self.gui.tempStatTable
        
        # Remove everything from table
        table.setRowCount(0)

        # Add all selected components back
        for comp in self.selectedComps:
            ma = str(self.extrema[comp]['glob_max'][1]) + '°C'
            mi = str(self.extrema[comp]['glob_min'][1]) + '°C'
            # Add row
            rowPosition = table.rowCount()
            table.insertRow(rowPosition)
            # Populate row
            table.setItem(rowPosition , 0, QtWidgets.QTableWidgetItem(comp))
            table.setItem(rowPosition , 1, QtWidgets.QTableWidgetItem(mi))
            table.setItem(rowPosition , 2, QtWidgets.QTableWidgetItem(ma))


    def updateTemps(self):
        """ Updates temporal plot based on component selection. """
        self.selectedComps = sorted([str(x.text()) for x in self.gui.compSelection.selectedItems()])

        for comp in self.data.keys():
            # If this component has NOT been plotted and is selected, plot it
            if comp not in self.plots.keys() and comp in self.selectedComps:
                plots = self.plotTemp(comp)
                self.visiblePlots.extend(plots)

            # If this component has been plotted and is selected and is hidden, show it
            elif comp in self.plots.keys() and comp in self.selectedComps and not self.get_visible(comp):
                for key, plot in self.plots[comp].iteritems():
                    plot.set_visible(True)
                    self.visiblePlots.append(plot)
                    # Add comp back to legend
                    if key == 'max':
                        self.handles.append(plot)
                        self.labels.append(comp)

            # If this component has been plotted and is not selected and is visible, hide it
            elif comp in self.plots.keys() and comp not in self.selectedComps and self.get_visible(comp):
                for key, plot in self.plots[comp].iteritems():
                    plot.set_visible(False)
                    self.visiblePlots.remove(plot)
                    # Remove plot from legend
                    if key == 'max':
                        self.handles.remove(plot)
                        self.labels.remove(comp)

        
        # Add legend
        self.drawLegend()

        # If zoom level is not fixed, rescale axes
        if not self.fixZoom:
            self.autoscale_based_on(self.visiblePlots)


    def drawLegend(self):
        """ Creates the legend for the temporal plot. """
        # Remove old legend
        if hasattr(self, 'templeg'):
            self.tempAxes.legend_.remove()

        # Create new legend
        if hasattr(self, 'handles'):
            self.templeg = self.tempAxes.legend(self.handles, self.labels)
            self.templeg.get_frame().set_alpha(0.4)
        
            # Allow some wiggle space when clicking on a legend line
            for legline in self.templeg.get_lines():
                legline.set_picker(5)

        ## Make legend handles pickable
        #for handle in self.templeg.legendHandles:
        #    handle.set_picker(True)
            
        self.canvas.mpl_connect('pick_event', self.changeColor)
        self.canvas.mpl_connect('motion_notify_event', self.changePointer)

        
    def changePointer(self, event):
        """ Changes the moise pointer when hovering the mouse over a legend handle. """
        handleBoxes = self.templeg.findobj(matplotlib.offsetbox.DrawingArea)

        for handleBox in handleBoxes:
            if handleBox.contains(event)[0]:
                QtWidgets.QApplication.setOverrideCursor(Qt.SizeAllCursor)
            else:
                QtWidgets.QApplication.restoreOverrideCursor()


    def autoscale_based_on(self, lines):
        """ Autoscales temporal axis based on pyplot 'Line2D' type <lines>. """
        ymax = -99999; ymin = 99999
        xmax = -99999; xmin = 99999
        for line in lines:
            if type(line).__name__ == 'Line2D':
                ymax = max(ymax,max(line.get_data()[1]))
                ymin = min(ymin,min(line.get_data()[1]))
                xmax = max(xmax,max(line.get_data()[0]))
                xmin = min(xmin,min(line.get_data()[0]))
        margin = self.tempMargin
        self.tempAxes.set_ylim([ymin - margin, ymax + margin])
        self.tempAxes.set_xlim([xmin, xmax])
        

    def plotTemp(self, comp):
        """ Plots the aquired temperature data against the time for a given component. """

        self.plots[comp] = {}
        x = []
        yMax = []
        yMin = []
        color = self.colors[comp]

        # Create plotable arrays from aquired temperature data
        for time in self.time:
            if time in self.data[comp]:
                x.append(time)
                yMax.append(self.data[comp][time]['Tmax'])
                yMin.append(self.data[comp][time]['Tmin'])

        # Global extrema
        Tmax_glob = self.extrema[comp]['glob_max']
        Tmin_glob = self.extrema[comp]['glob_min']
            
        # Plot data
        maxplt, =   self.tempAxes.plot(x,yMax, lw=2, color=color)
        minplt, =   self.tempAxes.plot(x,yMin, color=color, lw=2)
        max_glob =  self.tempAxes.scatter(Tmax_glob[0],Tmax_glob[1], marker="^", s=100, color=color)
        min_glob =  self.tempAxes.scatter(Tmin_glob[0],Tmin_glob[1], marker="v", s=100, color=color)
        fill =      self.tempAxes.fill_between(x,yMax,yMin,alpha=.5,facecolor=color)

        # Save plots per component so they can be switched on and off later
        self.plots[comp]['max'] = maxplt
        self.plots[comp]['min'] = minplt
        self.plots[comp]['max_glob'] = max_glob
        self.plots[comp]['min_glob'] = min_glob
        self.plots[comp]['fill'] = fill

        # Save one artist per component for populating the legend
        self.handles.append(maxplt)
        self.labels.append(comp)
        self.tempAxes.label=comp

        return [maxplt, minplt, max_glob, min_glob, fill]


    def get_visible(self, comp):
        """ Meant to determine visibility of all plots belonging to a component. Has to be a method of a new class Plot or so"""
        return all([plot.get_visible() for key, plot in self.plots[comp].iteritems()])
                        

    def updateExtrema(self):
        """ Updates the extrema plot based on the currently selected components. """
        self.selectedComps = sorted([str(x.text()) for x in self.gui.compSelection.selectedItems()])

        # Plotting all components again proved fast enough and is much
        # easier than retaining previously plotted lines
        self.extrAxes.clear()
        self.extrAxes.set_title("Absolute Extrema in Time and Space")
        self.ticklocs = []
        self.ticklabels = []
        for i, comp in enumerate(self.selectedComps):
            self.plotExtrema(i, comp)

        # Place and name ticks
        self.extrAxes.set_xticks([loc + self.width/2 for loc in self.ticklocs])
        self.extrAxes.tick_params(axis='x', which='both', length=0)
        self.extrAxes.set_xticklabels(self.ticklabels)

        # Add padding to every other ticklabel so they won't overlap
        for i, tick in enumerate(self.extrAxes.xaxis.get_major_ticks()):
            if i%2 == 0:
                tick.set_pad(20)

        # Add values above/below bars
        bars = self.extrAxes.patches
        vals = []
        for bar in bars:
            if bar.get_y() < 0:
                vals.append(bar.get_y())
            else:
                vals.append(bar.get_height())

        # Figure out how high the y-axis is
        ybottom, ytop = self.extrAxes.get_ylim() 
        yheight = ytop - ybottom

        # Place the labels in good positions depending on the height of the
        # bar and use height of y-axis as a scale for the padding
        for bar, val in zip(bars, vals):
            # If bar is positive, try to place label above it
            if val > 0:
                propHeight = val / ytop
                # If the bar is too high, place label inside
                if propHeight > .90: 
                    self.extrAxes.text(bar.get_x() + bar.get_width()/2, val - ytop*.04, str(val), ha='center', va='bottom')
                # Else, place label above
                else:
                    self.extrAxes.text(bar.get_x() + bar.get_width()/2, val + ytop*.01, str(val), ha='center', va='bottom')
            # If bar is negative, try to place label below it
            else:
                propHeight = val / ybottom
                # Note that ybottom is negative, so signs are reversed
                if propHeight > .95: 
                    self.extrAxes.text(bar.get_x() + bar.get_width()/2, val - ybottom*.01, str(val), ha='center', va='bottom')
                else:
                    self.extrAxes.text(bar.get_x() + bar.get_width()/2, val + ybottom*.04, str(val), ha='center', va='bottom')
        
        # Legend
        blue_patch = mpatches.Patch(color='blue', label='Minimum temperature')
        red_patch = mpatches.Patch(color='red', label='Maximum temperature')
        leg = self.extrAxes.legend(handles=[red_patch, blue_patch])
        leg.get_frame().set_alpha(0.4)

        
    def plotExtrema(self, ind, comp):
        """ Creates a new figure and canvas and plots the global extrema of the aquired temperature data for each component as a bar chart. """
        self.width = 0.35

        yMax = self.extrema[comp]['glob_max'][1]
        yMin = self.extrema[comp]['glob_min'][1]

        # Create plots
        self.extrPlots[comp] = {}
        self.extrPlots[comp]['extrMax'] = self.extrAxes.bar(ind, yMax, width=self.width, color='r', align='center')
        self.extrPlots[comp]['extrMin'] = self.extrAxes.bar(ind + self.width, yMin, width=self.width, color='b', align='center')

        self.ticklocs.append(ind)
        self.ticklabels.append(comp)


    def saveExtrema(self, saveFile):
        """ Writes temperature extrema for all components to a file. """
        logging.info("Writing temperature extrema to file {}".format(saveFile))
        f = open(saveFile,'w')

        # Write header
        f.write('##############################\n# ESATAN Evaluation - Case {}\n##############################\n\n'.format(self.caseComb))
        f.write('{:60s}{:15s}{:15s}\n'.format('Component','Tmax','Tmin'))
        string = ''
        
        # Write data
        for comp in self.data.keys():
            string += '{:60s}{:15s}{:15s}\n'.format(comp, str(self.extrema[comp]['glob_max'][1]), str(self.extrema[comp]['glob_min'][1]))
        
        f.write(string)
        f.close()


    def changeColor(self, event):
        """ 
        Gets called when a legend line was clicked. Finds the 
        corresponding component plots, prompts the user with a 
        colorpicker, applies the new color to the component plots,
        and re-draws the canvas.
        """
        # Legend line that was picked
        legline = event.artist

        # Find corresponding component
        ind = self.templeg.get_lines().index(legline)
        comp = self.templeg.get_texts()[ind].get_text()

        # Choose new color
        color = QtWidgets.QColorDialog.getColor()

        # Conversion to matplotlib-compatible rgb value
        red = color.red()/255
        blue = color.blue()/255
        green = color.green()/255
        rgb = (red,green,blue)

        # Update color for each plot belonging to this comp
        for key, plot in self.plots[comp].iteritems():
            plot.set_color(rgb)

        # Update legend
        self.drawLegend()

        # Save color so it is conserved if the artist is destroyed
        self.colors[comp] = rgb

        # Re-draw canvas
        self.canvas.draw_idle()



if __name__ == '__main__':

    logging.info("Starting application\n")
    app = QtWidgets.QApplication(sys.argv)

    main = ApplicationWindow()
    main.show()

    sys.exit(app.exec_())
