#!/usr/bin/env python3
import pickle,os,json
import numpy as np
import pandas as pd
import tkinter as tk
import tkinter.ttk
from radianceQuantifier.dataprocessing.inVivoRadianceImagePlotting import selectMatrices,plotMouseImages
from radianceQuantifier.dataprocessing.survivalProcessing import createSurvivalDf,createSurvivalPlot 
import radianceQuantifier.dataprocessing.miscFunctions as mf
import radianceQuantifier.plotting.facetPlotLibrary as fpl 
import radianceQuantifier.plotting.interactiveGUIElements as ipe
import matplotlib.colors as mcolors
import matplotlib.font_manager

if os.name == 'nt':
    dirSep = '\\'
else:
    dirSep = '/'
expParamDict = {'radiance':'cell'}

#Get level names and values into an easily accessible dictionary
def createLabelDict(df):
    fulldf = df.stack()
    labelDict = {}
    for i in range(fulldf.index.nlevels):
        levelName = fulldf.index.levels[i].name
        if levelName not in ['Event','event',None]:
            labelDict[levelName] = list(pd.unique(fulldf.index.get_level_values(levelName)))
    return labelDict

def createLabelDictWithExperimentParameters(df,experimentParameters):
    fulldf = df.stack()
    labelDict = {}
    for i in range(fulldf.index.nlevels):
        levelName = fulldf.index.levels[i].name
        if levelName in ['Event','event']:
            pass
        else:
            if 'allLevelValues' in list(experimentParameters.keys()):
                experimentParameters['levelLabelDict'] = experimentParameters['allLevelValues']
            if levelName in experimentParameters['levelLabelDict'].keys():
                if len(experimentParameters['levelLabelDict'][levelName]) > 0:
                    labelDict[levelName] = experimentParameters['levelLabelDict'][levelName]
                else:
                    labelDict[levelName] = list(pd.unique(fulldf.index.get_level_values(levelName)))
            else:
                labelDict[levelName] = list(pd.unique(fulldf.index.get_level_values(levelName)))
    return labelDict

class checkUncheckAllButton(tk.Button):
    def __init__(self,parent,checkButtonList,**kwargs):
        tk.Button.__init__(self,parent,**kwargs)
        self.checkButtonList = checkButtonList
        self.parent = parent

    def checkAll(self):
        for checkButton in self.checkButtonList:
            checkButton.select()
    
    def uncheckAll(self):
        for checkButton in self.checkButtonList:
            checkButton.deselect()

class PlotExperimentWindow(tk.Frame):
    def __init__(self, master,fName,sPage):
        with open('misc/normalPlottingBool.pkl','wb') as f:
            pickle.dump(True,f)

        global folderName,switchPage
            
        folderName = fName
        switchPage = sPage

        tk.Frame.__init__(self, master)
        
        experimentNameWindow = tk.Frame(self)
        experimentNameWindow.pack(side=tk.TOP,padx=10,pady=10)
        experimentNameLabel = tk.Label(experimentNameWindow,text=folderName+':').pack()

        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10,pady=10)
        
        l2 = tk.Label(mainWindow, text="""Datatype: """)
        v2 = tk.StringVar(value='radiance')
        rb2a = tk.Radiobutton(mainWindow, text="Radiance",padx = 20, variable=v2, value='radiance')
        rb2b = tk.Radiobutton(mainWindow,text="Mouse Images",padx = 20, variable=v2, value='mouseImages')
        rb2c = tk.Radiobutton(mainWindow,text="Survival",padx = 20, variable=v2, value='survival')
        
        l2.grid(row=0,column=0)
        rb2a.grid(row=1,column=0,sticky=tk.W)
        rb2b.grid(row=2,column=0,sticky=tk.W)
        rb2c.grid(row=3,column=0,sticky=tk.W)
        
        def collectInputs():
            global useModifiedDf
            modified = False 
            useModifiedDf = modified
            if modified:
                modifiedString = '-modified'
            else:
                modifiedString = ''
            global dataType
            dataType = str(v2.get())
            global experimentDf
            experimentDf = pd.read_pickle('outputData/radianceStatisticPickleFile-'+folderName+modifiedString+'.pkl')
            if dataType == 'radiance':
                experimentDf = experimentDf.droplevel('Day')
                experimentDf.columns.name = 'Statistic'
                indexingDf = experimentDf.copy()
                experimentDf = experimentDf.unstack('Time').stack('Statistic')
                for i in range(len(experimentDf.index.names)-1,0,-1):
                    experimentDf = experimentDf.swaplevel(i,i-1)
                global trueLabelDict
                trueLabelDict = {}
                if experimentDf.columns.name == None:
                    experimentDf.columns.name = 'Marker'
                for level in indexingDf.index.names:
                    if level in experimentDf.index.names:
                        swapIndex = list(experimentDf.index.names).index(level)
                        correctOrder = indexingDf.index.unique(level).tolist()
                        experimentDf = experimentDf.swaplevel(0,swapIndex).reindex(labels=correctOrder,level=0,axis='index').swaplevel(0,swapIndex)

                experimentParametersBool = False
                for fn in os.listdir('misc'):
                    if 'experimentParameters' in fn:
                        if expParamDict[dataType] in fn:
                            experimentParametersBool = True
                            experimentParameters = json.load(open('misc/experimentParameters-'+folderName+'-'+expParamDict[dataType]+'.json','r'))
                if experimentParametersBool:
                    trueLabelDict = createLabelDictWithExperimentParameters(experimentDf,experimentParameters)
                else:
                    trueLabelDict = createLabelDict(experimentDf)
                master.switch_frame(PlotTypePage)
            elif dataType == 'mouseImages':
                global pixelMatrix,minScaleDict
                pixelMatrix = np.load('outputData/'+folderName+'-pixel.npz')
                minScaleDict = pickle.load(open('outputData/'+folderName+'-minScale.pkl','rb'))
                master.switch_frame(MouseImageSelectionPage)
            #Survival
            else:
                global radianceStatisticDf
                radianceStatisticDf = pd.read_pickle('outputData/radianceStatisticPickleFile-'+folderName+'.pkl')
                master.switch_frame(SurvivalGroupSelectionPage)

        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)

        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).grid(row=5,column=0)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(switchPage,folderName)).grid(row=5,column=1)
        tk.Button(buttonWindow, text="Quit",command=quit).grid(row=5,column=2)

class SurvivalGroupSelectionPage(tk.Frame):
    def __init__(self, master):

        tk.Frame.__init__(self, master)
        labelWindow = tk.Frame(self)
        labelWindow.pack(side=tk.TOP,padx=10,fill=tk.X,expand=True)
        
        tk.Label(self,text='Select levels to keep separate in survival plot:',font='Helvetica 18 bold').pack(side=tk.TOP,padx=10,pady=10)
        
        checkButtonWindow = tk.Frame(self)
        checkButtonWindow.pack(side=tk.TOP)
        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10)
        
        levelsNotToInclude = ['Sample','Time','Day']
        trueLabelDict = createLabelDict(radianceStatisticDf.copy().droplevel(['Sample','Time','Day']))
        
        levelNameCheckButtons = []
        checkButtonVariableList = []
        for levelName,i in zip(trueLabelDict.keys(),range(len(trueLabelDict.keys()))):
            includeLevelBool = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(mainWindow, text=levelName,padx = 20, variable=includeLevelBool,onvalue=True)
            cb.grid(row=i+3,column=1,sticky=tk.W)
            cb.select()
            levelNameCheckButtons.append(cb)
            checkButtonVariableList.append(includeLevelBool)
        
        checkAllButton1 = checkUncheckAllButton(checkButtonWindow,levelNameCheckButtons, text='Check All')
        checkAllButton1.configure(command=checkAllButton1.checkAll)
        checkAllButton1.pack(side=tk.LEFT)
        
        uncheckAllButton1 = checkUncheckAllButton(checkButtonWindow,levelNameCheckButtons, text='Uncheck All')
        uncheckAllButton1.configure(command=checkAllButton1.uncheckAll)
        uncheckAllButton1.pack(side=tk.LEFT)

        def collectInputs():
            includeLevelList = []
            for checkButtonVariable in checkButtonVariableList:
                includeLevelList.append(checkButtonVariable.get())
            global survivalSelectionList,figureLevelList
            survivalSelectionList,figureLevelList = [],[]
            for figureLevelBool,levelName in zip(includeLevelList,trueLabelDict):
                if figureLevelBool:
                    figureLevelList.append(levelName)
                else:
                    survivalSelectionList.append(levelName)
            master.switch_frame(SelectSurvivalLevelValuesPage)

        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)

        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).grid(row=5,column=0)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(PlotExperimentWindow,folderName,switchPage)).grid(row=5,column=1)
        tk.Button(buttonWindow, text="Quit",command=quit).grid(row=5,column=2)

class SelectSurvivalLevelValuesPage(tk.Frame):
    def __init__(self, master):
        tk.Frame.__init__(self, master)
        
        levelsNotToInclude = ['Sample','Time','Day']
        trueLabelDict = createLabelDict(radianceStatisticDf.copy().droplevel(['Sample','Time','Day']))
        
        includeLevelValueList = []
        
        labelWindow = tk.Frame(self)
        labelWindow.pack(side=tk.TOP,padx=10,fill=tk.X,expand=True)
        
        l1 = tk.Label(labelWindow, text='Which specific level values do you want to include in the figure?',pady=10).grid(row=0,column = 0,columnspan=len(trueLabelDict)*6)
        levelValueCheckButtonList = []
        overallCheckButtonVariableList = []
        checkAllButtonList = []
        uncheckAllButtonList = []
        i=0
        maxNumLevelValues = 0
        for levelName in trueLabelDict:
            if len(trueLabelDict[levelName]) > maxNumLevelValues:
                maxNumLevelValues = len(trueLabelDict[levelName])
        """BEGIN TEMP SCROLLBAR CODE"""
        labelWindow1 = tk.Frame(self)
        labelWindow1.pack(side=tk.TOP,padx=10,fill=tk.X,expand=True)
        
        #Make canvas
        w1 = tk.Canvas(labelWindow1, width=1200, height=400, scrollregion=(0,0,2000,33*maxNumLevelValues))

        #Make scrollbar
        scr_v1 = tk.Scrollbar(labelWindow1,orient=tk.VERTICAL)
        scr_v1.pack(side=tk.RIGHT,fill=tk.Y)
        scr_v1.config(command=w1.yview)
        #Add scrollbar to canvas
        w1.config(yscrollcommand=scr_v1.set)
        
        scr_v2 = tk.Scrollbar(labelWindow1,orient=tk.HORIZONTAL)
        scr_v2.pack(side=tk.BOTTOM,fill=tk.X)
        scr_v2.config(command=w1.xview)
        w1.config(xscrollcommand=scr_v2.set)
        w1.pack(fill=tk.BOTH,expand=True)
        #Make and add frame for widgets inside of canvas
        #canvas_frame = tk.Frame(w1)
        labelWindow = tk.Frame(w1)
        labelWindow.pack()
        w1.create_window((0,0),window=labelWindow, anchor = tk.NW)
        """END TEMP SCROLLBAR CODE"""
        for levelName in trueLabelDict:
            j=0
            levelCheckButtonList = []
            levelCheckButtonVariableList = []
            levelLabel = tk.Label(labelWindow, text=levelName+':')
            levelLabel.grid(row=1,column = i*6,sticky=tk.N,columnspan=5)
            for levelValue in trueLabelDict[levelName]:
                includeLevelValueBool = tk.BooleanVar()
                cb = tk.Checkbutton(labelWindow, text=levelValue, variable=includeLevelValueBool)
                cb.grid(row=j+4,column=i*6+2,columnspan=2,sticky=tk.W)
                labelWindow.grid_columnconfigure(i*6+3,weight=1)
                cb.select()
                levelCheckButtonList.append(cb)
                levelCheckButtonVariableList.append(includeLevelValueBool)
                j+=1
            
            checkAllButton1 = checkUncheckAllButton(labelWindow,levelCheckButtonList, text='Check All')
            checkAllButton1.configure(command=checkAllButton1.checkAll)
            checkAllButton1.grid(row=2,column=i*6,sticky=tk.N,columnspan=3)
            checkAllButtonList.append(checkAllButton1)
            
            uncheckAllButton1 = checkUncheckAllButton(labelWindow,levelCheckButtonList, text='Uncheck All')
            uncheckAllButton1.configure(command=checkAllButton1.uncheckAll)
            uncheckAllButton1.grid(row=2,column=i*6+3,sticky=tk.N,columnspan=3)
            uncheckAllButtonList.append(checkAllButton1)

            levelValueCheckButtonList.append(levelCheckButtonList)
            overallCheckButtonVariableList.append(levelCheckButtonVariableList)
            i+=1

        def collectInputs():
            global survivalLevelValueList
            survivalLevelValueList = []
            for checkButtonVariableList in overallCheckButtonVariableList:
                tempLevelValueList = []
                for checkButtonVariable in checkButtonVariableList:
                    tempLevelValueList.append(checkButtonVariable.get())
                survivalLevelValueList.append(tempLevelValueList)
            master.switch_frame(AssignSurvivalLevelsToParametersPage)
        
        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)
        
        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).grid(row=maxNumLevelValues+4,column=0)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(SurvivalGroupSelectionPage)).grid(row=maxNumLevelValues+4,column=1)
        tk.Button(buttonWindow, text="Quit",command=lambda: quit()).grid(row=maxNumLevelValues+4,column=2)

class AssignSurvivalLevelsToParametersPage(tk.Frame):
    
    def __init__(self, master):
        plotType = '2d'
        parameterTypeDict = {
                'categorical':['Color','Order', 'Row', 'Column','None'],
                '1d':['Color','Row','Column','None'],
                '2d':['Marker','Color','Size','Row','Column','None'],
                '3d':['Row','Column','X Axis Values','Y Axis Values']}
        
        tk.Frame.__init__(self, master)
        levelsNotToInclude = ['Sample','Time','Day']
        trueLabelDict = createLabelDict(radianceStatisticDf.copy().droplevel(['Sample','Time','Day']))
        self.parametersSelected = {}
        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10,pady=10)
        
        l1 = tk.Label(mainWindow, text='Which plotting parameter do you want to assign to each of your figure levels?',pady=10).grid(row=0,column = 0,columnspan = len(figureLevelList))
        rblist = []
        parameterVarList = []
        for figureLevel,figureLevelIndex in zip(figureLevelList,range(len(figureLevelList))):
            v = tk.IntVar()
            temprblist = []
            levelLabel = tk.Label(mainWindow, text=figureLevel+':')
            levelLabel.grid(row=1,column=figureLevelIndex,sticky=tk.NW)
            for plottingParameter,parameterIndex in zip(parameterTypeDict[plotType],range(len(parameterTypeDict[plotType]))):
                rb = tk.Radiobutton(mainWindow, text=plottingParameter,padx = 20, variable=v, value=parameterIndex)
                rb.grid(row=parameterIndex+2,column=figureLevelIndex,sticky=tk.NW)
                temprblist.append(rb)
            rblist.append(temprblist)
            parameterVarList.append(v)
        
        def createPlot():
            #Assign plot parameters to level names
            for parameterVar,levelName in zip(parameterVarList,figureLevelList):
                if parameterTypeDict[plotType][parameterVar.get()] not in self.parametersSelected.keys():
                    self.parametersSelected[parameterTypeDict[plotType][parameterVar.get()]] = levelName
                else:
                    if not isinstance(self.parametersSelected[parameterTypeDict[plotType][parameterVar.get()]],list):
                        self.parametersSelected[parameterTypeDict[plotType][parameterVar.get()]] = [self.parametersSelected[parameterTypeDict[plotType][parameterVar.get()]]]+[levelName]
                    else:
                        self.parametersSelected[parameterTypeDict[plotType][parameterVar.get()]].append(levelName)
            
            #Query dataframe to only subset selected level values survivalSelectionList
            subsetDf = radianceStatisticDf.copy()
            for i,level in enumerate(trueLabelDict):
                booleanLevelValues = survivalLevelValueList[i]
                levelValues = [x for j,x in enumerate(trueLabelDict[level]) if booleanLevelValues[j]]
                subsetDf = subsetDf.query(level+" == @levelValues")
            #Legacy formatting
            subsetDf = subsetDf.droplevel('Time')
            subsetDf.index.names = [x if x != 'Day' else 'Time' for x in subsetDf.index.names]
            #Create titles
            if len(survivalSelectionList) != 0:
                outputName = '-'.join([folderName,'groupedBy='+','.join(survivalSelectionList),','.join([k+'='+self.parametersSelected[k] for k in self.parametersSelected if k != 'None'])])
            else:
                outputName = '-'.join([folderName,','.join([k+'='+self.parametersSelected[k] for k in self.parametersSelected if k != 'None'])])
            #Group dataframe correctly
            survivalDf = createSurvivalDf(subsetDf,survivalSelectionList,outputName,saveDf=False)
            #Create plot
            createSurvivalPlot(survivalDf,self.parametersSelected,outputName)
            tk.messagebox.showinfo(title='Success', message='Plot created!')
            self.FinishButton.config(state=tk.NORMAL)
            self.parametersSelected = {}

        def collectInputs():
            master.switch_frame(PlotExperimentWindow,folderName,switchPage)
        
        plotWindow = tk.Frame(self)
        plotWindow.pack(side=tk.TOP,pady=(10,0))
        tk.Button(plotWindow, text="Create plot",command=lambda: createPlot()).grid(row=0,column=0)

        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)
        
        self.FinishButton = tk.Button(buttonWindow, text="Finish",command=lambda: collectInputs())
        self.FinishButton.grid(row=len(parameterTypeDict[plotType])+2,column=0)
        self.FinishButton.config(state=tk.DISABLED)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(SelectSurvivalLevelValuesPage)).grid(row=len(parameterTypeDict[plotType])+2,column=1)
        tk.Button(buttonWindow, text="Quit",command=lambda: quit()).grid(row=len(parameterTypeDict[plotType])+2,column=2)

class MouseImageSelectionPage(tk.Frame):
    def __init__(self, master):

        tk.Frame.__init__(self, master)
        tk.Label(self,text='Select days and groups to plot:',font='Helvetica 18 bold').pack(side=tk.TOP,padx=10)
        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10,pady=(10,0))

        #Get input df
        if 'templatePathDict.pkl' in os.listdir(master.homedirectory + 'misc'):
            templatePathDict = pickle.load(open(master.homedirectory + 'misc/templatePathDict.pkl', 'rb'))
        else:
            templatePathDict = {}
        projectName = os.getcwd().split(dirSep)[(-2)]
        experimentName = os.getcwd().split(dirSep)[(-1)]
        templatePath = templatePathDict[projectName + '/' + experimentName]
        global sampleNameFile
        if '.csv' in templatePath:
            sampleNameFile = pd.read_csv(templatePath)
        else:
            sampleNameFile = pd.read_excel(templatePath)
        
        # remove extra columns that are empty
        sampleNameFile = sampleNameFile.dropna(axis=1, how='all')
        
        for i in range(sampleNameFile.shape[0]):
            for j in range(sampleNameFile.shape[1]):
                if not pd.isna(sampleNameFile.iloc[i,j]):
                    sampleNameFile.iloc[i,j] = str(sampleNameFile.iloc[i,j])
                    if sampleNameFile.iloc[i,j].replace(".", "",1).isdigit():
                        sampleNameFile.iloc[i,j] = sampleNameFile.iloc[i,j].rstrip("0").rstrip(".")

        #Ensure day names are compatible
        dayRenamingDict = {}
        for day in list(pd.unique(sampleNameFile['Day'])):
            newDay = 'D'+''.join([i for i in day if i.isdigit()])
            dayRenamingDict[day] = newDay
        dayIndex = list(sampleNameFile.columns).index('Day')
        for i in range(sampleNameFile.shape[0]):
            oldDay = sampleNameFile.iloc[i,dayIndex]
            sampleNameFile.iloc[i,dayIndex] = dayRenamingDict[oldDay]
        
        days = pd.unique(sampleNameFile['Day']).tolist()
        days = sorted(days, key=lambda x: int(''.join([s for s in x if s.isdigit()])))
        groups = pd.unique(sampleNameFile['Group']).tolist()
        groups = sorted(groups)

        dayWindow = tk.Frame(mainWindow)
        contentWindow = tk.Frame(dayWindow)
        contentWindow.grid(row=2,column=0)
        dayWindow.grid(row=0,column=0,sticky=tk.N)
        tk.Label(dayWindow,text='Day:').grid(row=0,column=0,sticky=tk.EW)

        dayCBList,dayCBVarList = [],[]
        for i,day in enumerate(days):
            includeVar = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(contentWindow,text=day,variable=includeVar)
            cb.grid(row=1+i,column=0,sticky=tk.W)
            dayCBList.append(cb)
            dayCBVarList.append(includeVar)
        
        checkButtonWindow = tk.Frame(dayWindow)
        checkAllButton1 = checkUncheckAllButton(checkButtonWindow,dayCBList, text='Check All')
        checkAllButton1.configure(command=checkAllButton1.checkAll)
        checkAllButton1.pack(side=tk.LEFT)
        uncheckAllButton1 = checkUncheckAllButton(checkButtonWindow,dayCBList, text='Uncheck All')
        uncheckAllButton1.configure(command=checkAllButton1.uncheckAll)
        uncheckAllButton1.pack(side=tk.LEFT)
        checkButtonWindow.grid(row=1,column=0,sticky=tk.EW)
        
        groupWindow = tk.Frame(mainWindow)
        groupWindow.grid(row=0,column=1,sticky=tk.N)
        contentWindow2 = tk.Frame(groupWindow)
        contentWindow2.grid(row=2,column=0)
        tk.Label(groupWindow,text='Group:').grid(row=0,column=0,sticky=tk.EW)
        groupCBList,groupCBVarList = [],[]
        #groupRenameEntryList = []
        for i,group in enumerate(groups):
            includeVar = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(contentWindow2,text=group,variable=includeVar)
            cb.grid(row=1+i,column=0,sticky=tk.W)
            groupCBList.append(cb)
            groupCBVarList.append(includeVar)
            #e = tk.Entry(contentWindow2)
            #e.grid(row=1+i,column=1,sticky=tk.W)
            #e.insert(tk.END, '')
            #groupRenameEntryList.append(e)
        
        checkButtonWindow2 = tk.Frame(groupWindow)
        checkAllButton2 = checkUncheckAllButton(checkButtonWindow2,groupCBList, text='Check All')
        checkAllButton2.configure(command=checkAllButton2.checkAll)
        checkAllButton2.pack(side=tk.LEFT)
        uncheckAllButton2 = checkUncheckAllButton(checkButtonWindow2,groupCBList, text='Uncheck All')
        uncheckAllButton2.configure(command=checkAllButton2.uncheckAll)
        uncheckAllButton2.pack(side=tk.LEFT)
        checkButtonWindow2.grid(row=1,column=0,sticky=tk.EW)
        
        def collectInputs():
            global selectedDays,selectedGroups
            selectedDays = [days[i] for i,x in enumerate(dayCBVarList) if x.get()]
            selectedGroups = [groups[i] for i,x in enumerate(groupCBVarList) if x.get()]
            #groupRenamingDict = {groups[i]:x.get() for i,x in enumerate(groupRenameEntryList) if x.get() != ''}
            master.switch_frame(MouseGroupRenamingPage)
            #master.switch_frame(MouseImagePlottingOptionsPage)

        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)

        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).grid(row=5,column=0)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(PlotExperimentWindow,folderName,switchPage)).grid(row=5,column=1)
        tk.Button(buttonWindow, text="Quit",command=quit).grid(row=5,column=2)

class MouseGroupRenamingPage(tk.Frame):
    def __init__(self, master):

        tk.Frame.__init__(self, master)
        tk.Label(self,text='Rename groups (if needed):',font='Helvetica 18 bold').pack(side=tk.TOP,padx=10)
        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10,pady=(10,0))
        
        groupRenameEntryList = []
        groupRecoloringEntryList = []
        defaultColorDict = mcolors.CSS4_COLORS 
        global indexNames
        columnsToKeep = [i for i,x in enumerate(list(sampleNameFile.columns)) if x not in ['Group','Day','SampleNames']]
        indexNames = [x for i,x in enumerate(list(sampleNameFile.columns)) if x not in ['Group','Day','SampleNames']]
        #tk.Label(mainWindow,text='Old').grid(row=0,column=0,sticky=tk.W)
        tk.Label(mainWindow,text='New group name').grid(row=0,column=1,sticky=tk.W)
        tk.Label(mainWindow,text='Text color').grid(row=0,column=2,sticky=tk.W)
        for i,selectedGroup in enumerate(selectedGroups):
            tk.Label(mainWindow,text=selectedGroup+' -> ').grid(row=i+1,column=0,sticky=tk.W)
            e = tk.Entry(mainWindow)
            e.grid(row=i+1,column=1,sticky=tk.W)
            indexList = sampleNameFile.query("Group == @selectedGroup").iloc[0,:].values.tolist()
            indexList = [x for i,x in enumerate(indexList) if i in columnsToKeep]
            defaultValue = ', '.join(indexList)
            e.insert(tk.END, defaultValue)
            groupRenameEntryList.append(e)
            textColorEntry = tkinter.ttk.Combobox(mainWindow,values=list(defaultColorDict.keys()))
            textColorEntry.grid(row=i+1,column=2,sticky=tk.W)
            textColorEntry.set('black')
            groupRecoloringEntryList.append(textColorEntry)

        def collectInputs():
            global groupRenamingDict
            global groupRecoloringDict
            groupRenamingDict = {selectedGroups[i]:x.get() for i,x in enumerate(groupRenameEntryList) if x.get() != ''}
            groupRecoloringDict = {selectedGroups[i]:x.get() for i,x in enumerate(groupRecoloringEntryList) if x.get() != ''}
            master.switch_frame(MouseImagePlottingOptionsPage)
        
        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)

        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).grid(row=5,column=0)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(MouseImageSelectionPage)).grid(row=5,column=1)
        tk.Button(buttonWindow, text="Quit",command=quit).grid(row=5,column=2)

class MouseImagePlottingOptionsPage(tk.Frame):
    def __init__(self, master):

        tk.Frame.__init__(self, master)
        tk.Label(self,text='Plot aesthetics:',font='Helvetica 18 bold').pack(side=tk.TOP,padx=10)
        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10,pady=(10,0))
        
        #Select dataframe first to get selection title
        subsetMatrix,selectionKeysDf,selectionTitle = selectMatrices(pixelMatrix,days=selectedDays,groups=selectedGroups)

        tk.Label(mainWindow,text='Color map:').grid(row=0,column=0,sticky=tk.W)
        defaultCmaps = ['turbo','viridis','plasma','inferno','magma','cividis']
        cmapEntry = tkinter.ttk.Combobox(mainWindow,values=defaultCmaps)
        cmapEntry.grid(row=0,column=1,sticky=tk.W)
        cmapEntry.set(defaultCmaps[0])

        tk.Label(mainWindow,text='Font Scale:').grid(row=1,column=0,sticky=tk.W)
        fontScaleEntry = tk.Entry(mainWindow)
        fontScaleEntry.grid(row=1,column=1,sticky=tk.W)
        fontScaleEntry.insert(tk.END, '1')
        
        tk.Label(mainWindow,text='Plot Title:').grid(row=2,column=0,sticky=tk.W)
        titleEntry = tk.Entry(mainWindow)
        titleEntry.grid(row=2,column=1,sticky=tk.W)
        titleEntry.insert(tk.END, selectionTitle)
        
        tk.Label(mainWindow,text='Column Title:').grid(row=3,column=0,sticky=tk.W)
        columnTitleEntry = tk.Entry(mainWindow)
        columnTitleEntry.grid(row=3,column=1,sticky=tk.W)
        columnTitleEntry.insert(tk.END, ', '.join(indexNames))
        
        tk.Label(mainWindow,text='Row Title:').grid(row=4,column=0,sticky=tk.W)
        rowTitleEntry = tk.Entry(mainWindow)
        rowTitleEntry.grid(row=4,column=1,sticky=tk.W)
        rowTitleEntry.insert(tk.END, 'Day')
        
        tk.Label(mainWindow,text='Group Order:').grid(row=5,column=0,sticky=tk.W)
        groupOrderEntry = tk.Entry(mainWindow)
        groupOrderEntry.grid(row=5,column=1,sticky=tk.W)
        groupOrderEntry.insert(tk.END, ','.join(list(groupRenamingDict.keys())))
        
        tailCropVar = tk.BooleanVar()
        tailCropCB = tk.Checkbutton(mainWindow,text='Crop tail',variable=tailCropVar)
        tailCropCB.select()
        tailCropCB.grid(row=6,column=0,columnspan=2,pady=5)
        

        tk.Label(mainWindow,text='Font:').grid(row=6,column=0,sticky=tk.W)
        
        fullFonts = matplotlib.font_manager.findSystemFonts()
        fontsToUse = ['Arial','Baskerville','Courier','Damascus','Didot','Futura','Georgia','GillSans','Helvetica','Impact','Palatino','Papyrus','Tahoma','Times New Roman','Trebuchet MS','Verdana'] 
        fontIndices = [i for i,x in enumerate(fullFonts) if x[x.rindex('/')+1:].split('.')[0] in fontsToUse]
        defaultFonts = sorted([x[x.rindex('/')+1:].split('.')[0] for i,x in enumerate(fullFonts) if i in fontIndices])
        
        fontEntry = tkinter.ttk.Combobox(mainWindow,values=defaultFonts)
        fontEntry.grid(row=6,column=1,sticky=tk.W)
        if 'Helvetica' in defaultFonts:
            fontEntry.set('Helvetica')
        else:
            fontEntry.set(defaultFonts[0])

        #defaultFormats = ['png','pdf']
        #tk.Label(mainWindow,text='File format:').grid(row=7,column=0,sticky=tk.W)
        #formatEntry = tkinter.ttk.Combobox(mainWindow,values=defaultFormats)
        #formatEntry.grid(row=7,column=1,sticky=tk.W)
        #formatEntry.set(defaultFormats[0])
        
        def createPlot():
            maxTextLength = len(max(list(groupRenamingDict.values()),key=len))
            plotMouseImages(subsetMatrix,minScaleDict,selectionKeysDf,titleRenamingDict={'row':rowTitleEntry.get(),'col':columnTitleEntry.get()},groupRecoloringDict=groupRecoloringDict,col_order=groupOrderEntry.get().split(','),tailCrop=tailCropVar.get(),innerCol='Sample',row='Day',col='Group',cmap=cmapEntry.get(),save_image=True,imageTitle=titleEntry.get(),fontScale=float(fontScaleEntry.get()),groupRenamingDict=groupRenamingDict,maxTextLength=maxTextLength,font=fontEntry.get(),fileFormat='png')#formatEntry.get())
            tk.messagebox.showinfo(title='Success', message='Plot created!')
            self.FinishButton.config(state=tk.NORMAL)

        def collectInputs():
            master.switch_frame(PlotExperimentWindow,folderName,switchPage)
        
        plotWindow = tk.Frame(self)
        plotWindow.pack(side=tk.TOP,pady=(10,0))
        tk.Button(plotWindow, text="Create plot",command=lambda: createPlot()).grid(row=0,column=0)

        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)

        self.FinishButton = tk.Button(buttonWindow, text="Finish",command=lambda: collectInputs())
        self.FinishButton.grid(row=5,column=0)
        self.FinishButton.config(state=tk.DISABLED)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(MouseGroupRenamingPage)).grid(row=5,column=1)
        tk.Button(buttonWindow, text="Quit",command=quit).grid(row=5,column=2)

class PlotTypePage(tk.Frame):
    def __init__(self, master):

        if 'normalPlottingBool.pkl' in os.listdir('misc'):
            normalPlottingBool = pickle.load(open('misc/normalPlottingBool.pkl','rb'))
        else:
            normalPlottingBool = True

        if not normalPlottingBool:
            global useModifiedDf,dataType,experimentDf,trueLabelDict,folderName,switchPage
            plottingParams = pickle.load(open('misc/plottingParams.pkl','rb'))
            useModifiedDf = False
            dataType = 'cell'
            experimentDf = plottingParams['df']
            trueLabelDict = createLabelDict(experimentDf)
            folderName = plottingParams['folderName']
            switchPage = 'a' 

        plottableFigureDict = {'1d':['histogram','kde'],'categorical':['bar','violin','box','point','swarm','strip'],'2d':['line','scatter'],'3d':['heatmap']}
        
        tk.Frame.__init__(self, master)
        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10)
        
        l1 = tk.Label(mainWindow, text="What type of figure do you want to plot?",pady=10).grid(row=0,column = 0,columnspan = len(plottableFigureDict),sticky=tk.N)
        
        #global trueLabelDict
        #trueLabelDict = {}
        #trueLabelDict = createLabelDict(experimentDf)
         
        plotTypeRadioButtons = []
        plotSelectionString = tk.StringVar(value='1d/histogram')
        maxNumSubplots = 0
        for plotTypeIndex,plotTypeTitle in enumerate(plottableFigureDict):
            plotTypeTitleLabel = tk.Label(mainWindow,text=plotTypeTitle).grid(row=1,column=plotTypeIndex,sticky=tk.NW)
            temprblist = []
            tempselectionstring = []
            for subPlotTypeIndex,subPlotTitle in enumerate(plottableFigureDict[plotTypeTitle]):
                rb = tk.Radiobutton(mainWindow, text=subPlotTitle,padx = 20, variable=plotSelectionString, value=plotTypeTitle+'/'+subPlotTitle)
                rb.grid(row=subPlotTypeIndex+2,column=plotTypeIndex,sticky=tk.NW)
                temprblist.append(rb)
            plotTypeRadioButtons.append(temprblist)
            if len(plottableFigureDict[plotTypeTitle]) > maxNumSubplots:
                maxNumSubplots = len(plottableFigureDict[plotTypeTitle])
        
        stripSwarmBool = tk.BooleanVar()
        cb = tk.Checkbutton(mainWindow,text='Add strip/swarm points to categorical plot',variable=stripSwarmBool,pady=20)
        cb.grid(row=maxNumSubplots+2,column=0,columnspan=len(plottableFigureDict))
        
        def collectInputs():
            global plotType
            global subPlotType
            global addDistributionPoints
            addDistributionPoints = stripSwarmBool.get()
            plotType,subPlotType = plotSelectionString.get().split('/')
            master.switch_frame(selectLevelsPage,'a','b','c','d','e')
        
        def backCommand():
            #os.chdir('../../')
            if normalPlottingBool:
                master.switch_frame(PlotExperimentWindow,folderName,switchPage)
            else:
                master.switch_frame(plottingParams['homepage'],folderName,plottingParams['bp'],plottingParams['shp'])
            #master.switch_frame(PlotExperimentWindow,switchPage)
       
        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP)
        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).pack(side=tk.LEFT)
        tk.Button(buttonWindow, text="Back",command=lambda: backCommand()).pack(side=tk.LEFT)
        tk.Button(buttonWindow, text="Quit",command=lambda: quit()).pack(side=tk.LEFT)

class selectLevelsPage(tk.Frame):
    def __init__(self, master,fsp,fName,backPage,pt,shp):
        tk.Frame.__init__(self, master)
        labelWindow = tk.Frame(self)
        labelWindow.pack(side=tk.TOP,padx=10,pady=10)
        
        global figureLevelList,fullFigureLevelBooleanList
        fullFigureLevelBooleanList = []
        figureLevelList = []
        
        l1 = tk.Label(labelWindow, text="""Which levels names do you want to be included within this figure??:""").pack()
        mainWindow = tk.Frame(self)
        levelNameCheckButtons = []
        checkButtonVariableList = []
        for levelName,i in zip(trueLabelDict.keys(),range(len(trueLabelDict.keys()))):
            includeLevelBool = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(mainWindow, text=levelName,padx = 20, variable=includeLevelBool,onvalue=True)
            cb.grid(row=i+3,column=1,sticky=tk.W)
            cb.select()
            levelNameCheckButtons.append(cb)
            checkButtonVariableList.append(includeLevelBool)
        
        checkButtonWindow = tk.Frame(self)
        checkAllButton1 = checkUncheckAllButton(checkButtonWindow,levelNameCheckButtons, text='Check All')
        checkAllButton1.configure(command=checkAllButton1.checkAll)
        checkAllButton1.pack(side=tk.LEFT)
        
        uncheckAllButton1 = checkUncheckAllButton(checkButtonWindow,levelNameCheckButtons, text='Uncheck All')
        uncheckAllButton1.configure(command=checkAllButton1.uncheckAll)
        uncheckAllButton1.pack(side=tk.LEFT)
        
        checkButtonWindow.pack(side=tk.TOP)
        mainWindow.pack(side=tk.TOP,padx=10)

        def collectInputs():
            includeLevelList = []
            for checkButtonVariable in checkButtonVariableList:
                includeLevelList.append(checkButtonVariable.get())
            for figureLevelBool,levelName in zip(includeLevelList,trueLabelDict):
                if figureLevelBool:
                    figureLevelList.append(levelName)
                    fullFigureLevelBooleanList.append(True)
                else:
                    fullFigureLevelBooleanList.append(False)
            master.switch_frame(selectLevelValuesPage,assignLevelsToParametersPage,trueLabelDict,selectLevelsPage,selectLevelsPage,fsp,fName,shp,'a')
        
        def quitCommand():
            exitBoolean = True
            quit()

        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)
        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).pack(in_=buttonWindow,side=tk.LEFT)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(PlotTypePage)).pack(in_=buttonWindow,side=tk.LEFT)
        tk.Button(buttonWindow, text="Quit",command=lambda: quitCommand()).pack(in_=buttonWindow,side=tk.LEFT)

class selectLevelValuesPage(tk.Frame):
    #(selectLevelValuesPage,SelectDimensionsPage,trueLabelDict,DataSelectionHomePage,finalSwitchPage,folderName,secondaryhomepage,processType)
    #master.switch_frame(selectLevelValuesPage,SelectDimensionsPage,trueLabelDict,DataSelectionHomePage,backpage,finalSwitchPage,folderName,secondaryhomepage,processType)
    def __init__(self, master,switchPage,trueLabelDict,backPage,secondaryBackPage,fsp,fName,shp,pt):
        tk.Frame.__init__(self, master)
        
        includeLevelValueList = []
        
        labelWindow = tk.Frame(self)
        labelWindow.pack(side=tk.TOP,padx=10,fill=tk.X,expand=True)
        
        l1 = tk.Label(labelWindow, text='Which specific level values do you want to include in the figure?',pady=10).grid(row=0,column = 0,columnspan=len(trueLabelDict)*6)
        levelValueCheckButtonList = []
        overallCheckButtonVariableList = []
        checkAllButtonList = []
        uncheckAllButtonList = []
        i=0
        maxNumLevelValues = 0
        for levelName in trueLabelDict:
            if len(trueLabelDict[levelName]) > maxNumLevelValues:
                maxNumLevelValues = len(trueLabelDict[levelName])
        """BEGIN TEMP SCROLLBAR CODE"""
        labelWindow1 = tk.Frame(self)
        labelWindow1.pack(side=tk.TOP,padx=10,fill=tk.X,expand=True)
        
        #Make canvas
        w1 = tk.Canvas(labelWindow1, width=1200, height=400, scrollregion=(0,0,2000,33*maxNumLevelValues))

        #Make scrollbar
        scr_v1 = tk.Scrollbar(labelWindow1,orient=tk.VERTICAL)
        scr_v1.pack(side=tk.RIGHT,fill=tk.Y)
        scr_v1.config(command=w1.yview)
        #Add scrollbar to canvas
        w1.config(yscrollcommand=scr_v1.set)
        
        scr_v2 = tk.Scrollbar(labelWindow1,orient=tk.HORIZONTAL)
        scr_v2.pack(side=tk.BOTTOM,fill=tk.X)
        scr_v2.config(command=w1.xview)
        w1.config(xscrollcommand=scr_v2.set)
        w1.pack(fill=tk.BOTH,expand=True)
        #Make and add frame for widgets inside of canvas
        #canvas_frame = tk.Frame(w1)
        labelWindow = tk.Frame(w1)
        labelWindow.pack()
        w1.create_window((0,0),window=labelWindow, anchor = tk.NW)
        """END TEMP SCROLLBAR CODE"""
        for levelName in trueLabelDict:
            j=0
            levelCheckButtonList = []
            levelCheckButtonVariableList = []
            levelLabel = tk.Label(labelWindow, text=levelName+':')
            levelLabel.grid(row=1,column = i*6,sticky=tk.N,columnspan=5)
            for levelValue in trueLabelDict[levelName]:
                includeLevelValueBool = tk.BooleanVar()
                cb = tk.Checkbutton(labelWindow, text=levelValue, variable=includeLevelValueBool)
                cb.grid(row=j+4,column=i*6+2,columnspan=2,sticky=tk.W)
                labelWindow.grid_columnconfigure(i*6+3,weight=1)
                cb.select()
                levelCheckButtonList.append(cb)
                levelCheckButtonVariableList.append(includeLevelValueBool)
                j+=1
            
            checkAllButton1 = checkUncheckAllButton(labelWindow,levelCheckButtonList, text='Check All')
            checkAllButton1.configure(command=checkAllButton1.checkAll)
            checkAllButton1.grid(row=2,column=i*6,sticky=tk.N,columnspan=3)
            checkAllButtonList.append(checkAllButton1)
            
            uncheckAllButton1 = checkUncheckAllButton(labelWindow,levelCheckButtonList, text='Uncheck All')
            uncheckAllButton1.configure(command=checkAllButton1.uncheckAll)
            uncheckAllButton1.grid(row=2,column=i*6+3,sticky=tk.N,columnspan=3)
            uncheckAllButtonList.append(checkAllButton1)

            levelValueCheckButtonList.append(levelCheckButtonList)
            overallCheckButtonVariableList.append(levelCheckButtonVariableList)
            i+=1

        def collectInputs():
            for checkButtonVariableList in overallCheckButtonVariableList:
                tempLevelValueList = []
                for checkButtonVariable in checkButtonVariableList:
                    tempLevelValueList.append(checkButtonVariable.get())
                includeLevelValueList.append(tempLevelValueList)
            #master.switch_frame(assignLevelsToParametersPage)
            master.switch_frame(switchPage,includeLevelValueList)
        
        def quitCommand():
            exitBoolean = True
            quit()
        
        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)
        
        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).grid(row=maxNumLevelValues+4,column=0)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(backPage,fsp,fName,secondaryBackPage,pt,shp)).grid(row=maxNumLevelValues+4,column=1)
        tk.Button(buttonWindow, text="Quit",command=lambda: quitCommand()).grid(row=maxNumLevelValues+4,column=2)

class assignLevelsToParametersPage(tk.Frame):
    
    def __init__(self, master,temp):
        parameterTypeDict = {
                'categorical':['Color','Order', 'Row', 'Column','None'],
                '1d':['Color','Row','Column','None'],
                '2d':['Marker','Color','Size','Row','Column','X Axis Values','None'],
                '3d':['Row','Column','X Axis Values','Y Axis Values']}
        
        tk.Frame.__init__(self, master)
        global includeLevelValueList
        includeLevelValueList = temp
        global parametersSelected
        parametersSelected = {}
        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10,pady=10)
        
        l1 = tk.Label(mainWindow, text='Which plotting parameter do you want to assign to each of your figure levels?',pady=10).grid(row=0,column = 0,columnspan = len(figureLevelList))
        rblist = []
        parameterVarList = []
        for figureLevel,figureLevelIndex in zip(figureLevelList,range(len(figureLevelList))):
            v = tk.IntVar()
            temprblist = []
            levelLabel = tk.Label(mainWindow, text=figureLevel+':')
            levelLabel.grid(row=1,column=figureLevelIndex,sticky=tk.NW)
            for plottingParameter,parameterIndex in zip(parameterTypeDict[plotType],range(len(parameterTypeDict[plotType]))):
                rb = tk.Radiobutton(mainWindow, text=plottingParameter,padx = 20, variable=v, value=parameterIndex)
                rb.grid(row=parameterIndex+2,column=figureLevelIndex,sticky=tk.NW)
                temprblist.append(rb)
            rblist.append(temprblist)
            parameterVarList.append(v)
        
        def collectInputs():
            for parameterVar,levelName in zip(parameterVarList,figureLevelList):
                if parameterTypeDict[plotType][parameterVar.get()] not in parametersSelected.keys():
                    parametersSelected[parameterTypeDict[plotType][parameterVar.get()]] = levelName
                else:
                    if not isinstance(parametersSelected[parameterTypeDict[plotType][parameterVar.get()]],list):
                        parametersSelected[parameterTypeDict[plotType][parameterVar.get()]] = [parametersSelected[parameterTypeDict[plotType][parameterVar.get()]]]+[levelName]
                    else:
                        parametersSelected[parameterTypeDict[plotType][parameterVar.get()]].append(levelName)
            master.switch_frame(plotElementsGUIPage)
        
        def quitCommand():
            exitBoolean = True
            quit()
        
        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)
        
        tk.Button(buttonWindow, text="OK",command=lambda: collectInputs()).grid(row=len(parameterTypeDict[plotType])+2,column=0)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(selectLevelValuesPage,assignLevelsToParametersPage,trueLabelDict,selectLevelsPage,'a','b','c','d','e')).grid(row=len(parameterTypeDict[plotType])+2,column=1)
        tk.Button(buttonWindow, text="Quit",command=lambda: quitCommand()).grid(row=len(parameterTypeDict[plotType])+2,column=2)

def getDefaultAxisTitles():
        xaxistitle = ''
        yaxistitle = ''
        cbartitle = ''
        cytokineDefault = 'Concentration (nM)'
        if plotType == '1d':
            xaxistitle = 'MFI'
            yaxistitle = 'Frequency'
        else:
            if plotType == 'categorical':
                xaxistitle = parametersSelected['Order']
                if dataType == 'cyt':
                    yaxistitle = cytokineDefault
            else:
                xaxistitle = parametersSelected['X Axis Values']
                if dataType == 'cyt':
                    if plotType == '2d':
                        yaxistitle = cytokineDefault
                    else:
                        cbartitle = cytokineDefault
        if xaxistitle == 'Time':
            xaxistitle += ' (days)'
        return [xaxistitle,yaxistitle,cbartitle]

class plotElementsGUIPage(tk.Frame):
    def __init__(self, master):
        if 'experimentParameters-'+folderName+'-'+expParamDict[dataType]+'.json' in os.listdir('misc'):
            experimentParameters = json.load(open('misc/experimentParameters-'+folderName+'-'+expParamDict[dataType]+'.json','r'))
        else:
            tempDict = {}
            stackedDf = experimentDf.stack()
            for level in stackedDf.index.names:
                levelValues = list(pd.unique(stackedDf.index.get_level_values(level)))
                tempDict[level] = levelValues
            experimentParameters = {}
            experimentParameters['levelLabelDict'] = tempDict
        """ 
        global dataType
        if 'cell' in pickleFileName: 
            dataType = 'cell'
        elif 'cyt' in pickleFileName:
            dataType = 'cyt'
        elif 'prolif' in pickleFileName:
            dataType = 'prolif'
        else:
            dataType = ''
        """
        self.tld = trueLabelDict

        axisDict = {'categorical':['X','Y'],'1d':['Y'],'2d':['X','Y'],'3d':['X','Y','Colorbar']}
        scalingList = ['Linear','Logarithmic','Biexponential']
        axisSharingList = ['col','row','']
        axisTitleDefaults = getDefaultAxisTitles() 
        
        tk.Frame.__init__(self, master)
        
        mainWindow = tk.Frame(self)
        mainWindow.pack(side=tk.TOP,padx=10,pady=10)

        tk.Label(mainWindow, text='Title: ').grid(row=1,column=0,sticky=tk.W)
        for scaling,scalingIndex in zip(scalingList,range(len(scalingList))):
            tk.Label(mainWindow, text=scaling+' Scaling: ').grid(row=scalingIndex+2,column=0,sticky=tk.W)
        tk.Label(mainWindow, text='Linear Range (Biexponential Scaling): ').grid(row=len(scalingList)+2,column=0,sticky=tk.W)
        tk.Label(mainWindow, text='Convert to numeric: ').grid(row=len(scalingList)+3,column=0,sticky=tk.W)
        tk.Label(mainWindow, text='Share axis across: ').grid(row=len(scalingList)+4,column=0,sticky=tk.W)
        tk.Label(mainWindow, text='Axis limits: ').grid(row=len(scalingList)+5,column=0,sticky=tk.W)

        entryList = []
        scalingVariableList = []
        radioButtonList = []
        checkButtonList = []
        checkButtonVarList = []
        radioButtonList2 = []
        radioButtonVarList2 = []
        linearRangeScalingList = []
        limitEntryList = []
        for axis,axisIndex in zip(axisDict[plotType],range(len(axisDict[plotType]))):
            tk.Label(mainWindow, text=axis+ ' Axis').grid(row=0,column=axisIndex+1)
            
            e1 = tk.Entry(mainWindow)
            e1.grid(row=1,column=axisIndex+1)
            e1.insert(0, axisTitleDefaults[axisIndex])
            entryList.append(e1)
            
            axisRadioButtonList = []
            v = tk.StringVar(value='Linear')
            for scaling,scalingIndex in zip(scalingList,range(len(scalingList))):
                rb = tk.Radiobutton(mainWindow,variable=v,value=scaling)
                rb.grid(row=scalingIndex+2,column=axisIndex+1)
                axisRadioButtonList.append(rb)
            radioButtonList.append(axisRadioButtonList)
            scalingVariableList.append(v)
            
            e2 = tk.Entry(mainWindow)
            e2.grid(row=len(scalingList)+2,column=axisIndex+1)
            linearRangeScalingList.append(e2)
            
            b = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(mainWindow,variable=b)
            cb.grid(row=len(scalingList)+3,column=axisIndex+1)
            checkButtonList.append(cb)
            checkButtonVarList.append(b)
       
            shareWindow = tk.Frame(mainWindow)
            shareWindow.grid(row=len(scalingList)+4,column=axisIndex+1)
            shareString = tk.StringVar(value='None')
            rb2a = tk.Radiobutton(shareWindow,variable=shareString,text='All',value='all')
            rb2b = tk.Radiobutton(shareWindow,variable=shareString,text='Row',value='row')
            rb2c = tk.Radiobutton(shareWindow,variable=shareString,text='Col',value='col')
            rb2d = tk.Radiobutton(shareWindow,variable=shareString,text='None',value='none')
            shareString.set('all')
            rb2a.grid(row=0,column=1)
            rb2b.grid(row=0,column=2)
            rb2c.grid(row=0,column=3)
            rb2d.grid(row=0,column=4)
            radioButtonList2.append([rb2a,rb2b])
            radioButtonVarList2.append(shareString)

            limitWindow = tk.Frame(mainWindow)
            limitWindow.grid(row=len(scalingList)+5,column=axisIndex+1)
            #ll = tk.Label(limitWindow,text='Lower:').grid(row=0,column=0)
            e3 = tk.Entry(limitWindow,width=5)
            e3.grid(row=0,column=1)
            #ul = tk.Label(limitWindow,text='Upper:').grid(row=0,column=2)
            e4 = tk.Entry(limitWindow,width=5)
            e4.grid(row=0,column=3)
            limitEntryList.append([e3,e4])

        def collectInputs(plotAllVar):
            plotOptions = {}
            for axis,axisIndex in zip(axisDict[plotType],range(len(axisDict[plotType]))):
                share = radioButtonVarList2[axisIndex].get()
                if share == 'none':
                    share = False
                plotOptions[axis] = {'axisTitle':entryList[axisIndex].get(),
                        'axisScaling':scalingVariableList[axisIndex].get(),
                        'linThreshold':linearRangeScalingList[axisIndex].get(),
                        'numeric':checkButtonVarList[axisIndex].get(),
                        'share':share,
                        'limit':[limitEntryList[axisIndex][0].get(),limitEntryList[axisIndex][1].get()]}
            
            plotSpecificDict = {}
            if subPlotType == 'kde':
                scaleBool = ipe.getRadiobuttonValues(modeScaleRadiobuttonVarsDict)['scale to mode']
                if scaleBool == 'yes':
                    plotSpecificDict['scaleToMode'] = True
                else:
                    plotSpecificDict['scaleToMode'] = False
                plotSpecificDict['smoothing'] = int(ipe.getSliderValues(smoothingSliderList,['smoothing'])['smoothing'])
            elif subPlotType == 'line':
                ciType = ipe.getRadiobuttonValues(ciSelectionRadiobuttonVarsDict)['Error bar']
                errType = ipe.getRadiobuttonValues(ciStyleSelectionRadiobuttonVarsDict)['Error bar style']
                if ciType == 'st dev':
                    plotSpecificDict['ci'] = 'sd'
                elif ciType == 'conf int':
                    plotSpecificDict['ci'] = 95

                if errType == 'band' and ciType in ['st dev','conf int']:
                    plotSpecificDict['err_style'] = 'band'
                elif errType == 'bar' and ciType in ['st dev','conf int']:
                    plotSpecificDict['err_style'] = 'bars'
            
            useModifiedDf = False
            sName = titleEntry.get()
            subsettedDfList,subsettedDfListTitles,figureLevels,levelValuesPlottedIndividually = fpl.produceSubsettedDataFrames(experimentDf.stack().to_frame('temp'),fullFigureLevelBooleanList,includeLevelValueList,self.tld)
            fpl.plotFacetedFigures(folderName,plotType,subPlotType,dataType,subsettedDfList,subsettedDfListTitles,figureLevels,levelValuesPlottedIndividually,useModifiedDf,experimentDf,plotOptions,parametersSelected,addDistributionPoints,originalLevelValueOrders=experimentParameters['levelLabelDict'],subfolderName=sName,context=ipe.getRadiobuttonValues(contextRadiobuttonVarsDict)['context'],height=float(heightEntry.get()),aspect=float(widthEntry.get()),titleBool=ipe.getRadiobuttonValues(plotTitleRadiobuttonVarsDict)['plotTitle'],colwrap=int(colWrapEntry.get()),legendBool=ipe.getRadiobuttonValues(legendRadiobuttonVarsDict)['legend'],cmap=cmapEntry.get(),plotAllVar=plotAllVar,titleAdjust=titleAdjustEntry.get(),plotSpecificDict = plotSpecificDict)
            
        titleWindow = tk.Frame(self)
        titleWindow.pack(side=tk.TOP,pady=10)
        tk.Label(titleWindow,text='Enter subfolder for these plots (optional):').grid(row=0,column=0)
        titleEntry = tk.Entry(titleWindow,width=15)
        titleEntry.grid(row=0,column=1)
        
        miscOptionsWindow = tk.Frame(self)
        miscOptionsWindow.pack(side=tk.TOP,pady=10)
        
        contextWindow = tk.Frame(miscOptionsWindow)
        contextWindow.grid(row=0,column=0,sticky=tk.N)
        contextRadiobuttonList,contextRadiobuttonVarsDict = ipe.createParameterSelectionRadiobuttons(contextWindow,['context'],{'context':['notebook','talk','poster']}) 
        
        figureDimensionWindow = tk.Frame(miscOptionsWindow)
        figureDimensionWindow.grid(row=0,column=1,sticky=tk.N)
        tk.Label(figureDimensionWindow,text='figure dimensions').grid(row=0,column=0)
        tk.Label(figureDimensionWindow,text='height:').grid(row=1,column=0)
        tk.Label(figureDimensionWindow,text='width:').grid(row=2,column=0)
        heightEntry = tk.Entry(figureDimensionWindow,width=3)
        if plotType != '1d':
            heightEntry.insert(0, '5')
        else:
            heightEntry.insert(0, '3')
        widthEntry = tk.Entry(figureDimensionWindow,width=3)
        widthEntry.insert(0, '1')
        heightEntry.grid(row=1,column=1)
        widthEntry.grid(row=2,column=1)
        
        plotTitleWindow = tk.Frame(miscOptionsWindow)
        plotTitleWindow.grid(row=0,column=2,sticky=tk.N)
        plotTitleRadiobuttonList,plotTitleRadiobuttonVarsDict = ipe.createParameterSelectionRadiobuttons(plotTitleWindow,['plotTitle'],{'plotTitle':['yes','no']}) 
        
        legendWindow = tk.Frame(miscOptionsWindow)
        legendWindow.grid(row=0,column=3,sticky=tk.N)
        legendRadiobuttonList,legendRadiobuttonVarsDict = ipe.createParameterSelectionRadiobuttons(legendWindow,['legend'],{'legend':['yes','no']}) 
        
        colWrapWindow = tk.Frame(miscOptionsWindow)
        colWrapWindow.grid(row=0,column=4,sticky=tk.N)
        tk.Label(colWrapWindow,text='column wrap:').grid(row=0,column=0)
        colWrapEntry = tk.Entry(colWrapWindow,width=5)
        colWrapEntry.insert(0, '5')
        colWrapEntry.grid(row=1,column=0)
        
        titleAdjustWindow = tk.Frame(miscOptionsWindow)
        titleAdjustWindow.grid(row=0,column=5,sticky=tk.N)
        tk.Label(titleAdjustWindow,text='title location (% of window):').grid(row=0,column=0)
        titleAdjustEntry = tk.Entry(titleAdjustWindow,width=5)
        titleAdjustEntry.insert(0, '')
        titleAdjustEntry.grid(row=1,column=0)
        
        #outlierWindow = tk.Frame(miscOptionsWindow)
        #outlierWindow.grid(row=0,column=6,sticky=tk.N)
        #outlierRadiobuttonList,outlierRadiobuttonVarsDict = ipe.createParameterSelectionRadiobuttons(outlierWindow,['remove outliers'],{'remove outliers':['yes','no']}) 
        #outlierRadiobuttonVarsDict['remove outliers'].set('no')
        
        cmapWindow = tk.Frame(miscOptionsWindow)
        cmapWindow.grid(row=0,column=6,sticky=tk.N)
        tk.Label(cmapWindow,text='Colormap:').grid(row=0,column=0)
        cmapEntry = tk.Entry(cmapWindow,width=10)
        cmapEntry.grid(row=1,column=0)
        
        if subPlotType == 'kde':
            #Scale to mode button
            subPlotSpecificWindow = tk.Frame(self)
            subPlotSpecificWindow.pack(side=tk.TOP,pady=10)
            modeScaleWindow = tk.Frame(subPlotSpecificWindow)
            modeScaleWindow.grid(row=0,column=0,sticky=tk.N)
            modeScaleRadiobuttonList,modeScaleRadiobuttonVarsDict = ipe.createParameterSelectionRadiobuttons(modeScaleWindow,['scale to mode'],{'scale to mode':['yes','no']}) 
            modeScaleRadiobuttonVarsDict['scale to mode'].set('no')
            #Smoothness (or bandwidth) slider
            smoothnessWindow = tk.Frame(subPlotSpecificWindow)
            smoothnessWindow.grid(row=0,column=1,sticky=tk.N)
            smoothingSliderList = ipe.createParameterAdjustmentSliders(smoothnessWindow,['smoothing'],{'smoothing':[1,99,2,27]})
        elif subPlotType in ['line']:
            #Scale to mode button
            subPlotSpecificWindow = tk.Frame(self)
            subPlotSpecificWindow.pack(side=tk.TOP,pady=10)

            ciSelectionWindow = tk.Frame(subPlotSpecificWindow)
            ciSelectionWindow.grid(row=0,column=0,sticky=tk.N)
            ciSelectionRadiobuttonList,ciSelectionRadiobuttonVarsDict = ipe.createParameterSelectionRadiobuttons(ciSelectionWindow,['Error bar'],{'Error bar':['none','st dev','conf int']})
            ciSelectionRadiobuttonVarsDict['Error bar'].set('none')

            ciStyleSelectionWindow = tk.Frame(subPlotSpecificWindow)
            ciStyleSelectionWindow.grid(row=0,column=1,sticky=tk.N)
            ciStyleSelectionRadiobuttonList,ciStyleSelectionRadiobuttonVarsDict = ipe.createParameterSelectionRadiobuttons(ciStyleSelectionWindow,['Error bar style'],{'Error bar style':['bar','band']})
            ciStyleSelectionRadiobuttonVarsDict['Error bar style'].set('bar')



        plotButtonWindow = tk.Frame(self)
        plotButtonWindow.pack(side=tk.TOP,pady=10)
        tk.Button(plotButtonWindow, text="Generate First Plot",command=lambda: collectInputs(False)).grid(row=0,column=0)
        tk.Button(plotButtonWindow, text="Generate All Plots",command=lambda: collectInputs(True)).grid(row=0,column=1)
        
        buttonWindow = tk.Frame(self)
        buttonWindow.pack(side=tk.TOP,pady=10)
        
        def okCommand():
            master.switch_frame(PlotTypePage)
        
        tk.Button(buttonWindow, text="Finish",command=lambda: okCommand()).grid(row=len(scalingList)+4,column=0)
        tk.Button(buttonWindow, text="Back",command=lambda: master.switch_frame(assignLevelsToParametersPage,includeLevelValueList)).grid(row=len(scalingList)+4,column=1)
        tk.Button(buttonWindow, text="Quit",command=lambda: quit()).grid(row=len(scalingList)+4,column=2)
