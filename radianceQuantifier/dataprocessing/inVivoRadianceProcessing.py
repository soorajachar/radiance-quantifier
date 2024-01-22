#General purpose data wrangling/visualization packages
import pandas as pd
import seaborn as sns
import numpy as np
import matplotlib
from matplotlib.colors import LogNorm
import matplotlib.pyplot as plt
import os,pickle,sys,shutil
from sklearn.preprocessing import MinMaxScaler
sns.set_context('talk')

#Image processing packages
from matplotlib import image as mplImage
import pytesseract
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    dirSep = '\\'
else:
    dirSep = '/'
from PIL import Image
from scipy import ndimage
import cv2
import imutils
from kneed import KneeLocator
import statsmodels.api as sm

#Clustering
import hdbscan

#Plotting
from radianceQuantifier.plotting.plottingFunctions import slanted_images_summary_plot, plot_image_widths, plot_image, plot_slanted_image

#Miscellaneous
from itertools import tee
from tqdm.auto import trange, tqdm
from scipy.signal import argrelmin,find_peaks,savgol_filter
import warnings
import shutil
from radianceQuantifier.dataprocessing.miscFunctions import loadPickle, selectMatrices, loadNPZ

warnings.filterwarnings("ignore")

referencePercentiles = [155,191,213,229,240,249,256,261,266,270,273,277,280,283,286,288,292,295,297,299,303,305,307,310,312,314,316,318,321,323,325,327,329,331,333,335,337,340,342,344,346,349,351,354,356,359,362,365,368,371,375,379,383,387,392,398,404,410,418,426,437,450,466,487,511,538,570,609,656,715,793,893,1012,1162,1351,1571,1789,1996,2190,2366,2526,2686,2850,3015,3172,3325,3461,3585,3706,3818,3922,4019,4112,4201,4289,4379,4475,4576,4690,4844,5713]

def ranges(nums):
    nums = sorted(set(nums))
    gaps = [[s, e] for s, e in zip(nums, nums[1:]) if s+1 < e]
    edges = iter(nums[:1] + sum(gaps, []) + nums[-1:])
    return list(zip(edges, edges))

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def get_blocks(values,cutoff):
    result = []
    for i,val in enumerate(values):
        values2 = [values[x] for x in range(len(values)) if x != i]
        group = [val]
        for val2 in values2:
            if abs(val2 - val) < cutoff:
                group.append(val2)
        result.append(group)
    return result

def np_array_to_hex(array):
    array = np.asarray(array, dtype='uint32')
    array = ((array[:, :, 0]<<16) + (array[:, :, 1]<<8) + array[:, :, 2])
    return array

def img_array_to_single_val(image, color_codes):
    image = image.dot(np.array([65536, 256, 1], dtype='int32'))
    result = np.ndarray(shape=image.shape, dtype=int)
    result[:,:] = -1
    for rgb, idx in color_codes.items():
        rgb = rgb[0] * 65536 + rgb[1] * 256 + rgb[2]
        result[image==rgb] = idx
    return result

def transparent_cmap(cmap, N=255):
    "Copy colormap and set alpha values"

    mycmap = cmap
    mycmap._init()
    #mycmap._lut[:,-1] = np.linspace(0, 0.8, N+4)
    mycmap._lut[0,-1] = 0
    return mycmap

def returnColorScale(colorBar):    
    rgbaList = np.dsplit(colorBar,colorBar.shape[2])
    colorDfList = []
    for d in rgbaList:
        colorDf = pd.DataFrame(d[:,:,0],index=list(range(colorBar.shape[0])),columns=list(range(colorBar.shape[1])))
        colorDf.index.name = 'Row'
        colorDf.columns.name = 'Column'
        colorDfList.append(colorDf)
    colorDf = pd.concat(colorDfList,keys=['R','G','B','A'],names=['Color'])
    colorScale = colorDf.loc[['R','G','B']].iloc[:,int(colorDf.shape[1]/2)].unstack('Color').values.tolist()[::-1] + [[1,0,0]]

    rgbColorScale = []
    for elem in colorScale:
        elem = [int(255*x) for x in elem]
        rgbColorScale.append(elem)
    
    trueRGBColorScale = []
    offset = 1
    for r in range(rgbColorScale[0][0]+offset,-1,-1):
        trueRGBColorScale.append([r,0,255])
    for g in range(1,256):
        trueRGBColorScale.append([0,g,255])
    for b in range(255,-1,-1):
        trueRGBColorScale.append([0,255,b])
    for r in range(1,256):
        trueRGBColorScale.append([r,255,0])
    for g in range(255,-1,-1):
        trueRGBColorScale.append([255,g,0])

    return trueRGBColorScale

def returnColorScaleSpan(legend,colorScale,colorBarScale,cbar_lim=[]):
    
    #If using pytesseract to read in colorbar scale limits
    if len(cbar_lim) == 0:
        splitChar = True
        croppedLegend = np.multiply(legend[60:105,:75],255)
        pIm = Image.fromarray(np.uint8(croppedLegend))
        fullString = pytesseract.image_to_string(pIm)
        splitStrings = fullString.split('\n')
        for splitString in splitStrings:
            if 'Min' in splitString or 'Max' in splitString:
              #Account for occasinoal pytesseract failures
              if ' = ' in splitString:
                splitChar = ' = '
              else:
                if ' =' in splitString:
                  splitChar = ' ='
                elif '= ' in splitString:
                  splitChar = '= '
                else:
                  if '=' in splitString:
                    splitChar = '='
                  else:
                    splitChar = False
              if splitChar:
                  if 'Min' in splitString:
                      number = splitString.split(splitChar)[1]
                      minScalingFactor = 10**int(number[-1])
                      scaleStart = float(number[:4])*minScalingFactor
                      hasMin = True
                  elif 'Max' in splitString:
                      number = splitString.split(splitChar)[1]
                      maxScalingFactor = 10**int(number[-1])
                      scaleEnd = float(number[:4])*maxScalingFactor
                      hasMax = True
        if hasMin and hasMax:
            linearScale = np.linspace(scaleStart,scaleEnd,num=len(colorScale))
            return linearScale,scaleStart
        else:
            raise NameError('pytesseract automatic colorbar reading failed! Try setting a MANUAL axis limit instead')
    else:
        scaleStart = cbar_lim[0]
        scaleEnd = cbar_lim[1]
        linearScale = np.linspace(scaleStart,scaleEnd,num=len(colorScale))
        return linearScale,scaleStart

def returnLuminescentImageComponents(luminescent,visualize=False):
    occupancyCutoff = 300
    headerCutoff = 50

    rgbSample = luminescent[:,:,:]
    #Separate colorbar from mouse samples
    bwMatrix = np.zeros(luminescent.shape)[:,:,:]
    for row in range(luminescent.shape[0]):
        for col in range(luminescent.shape[1]):
            pixel = luminescent[row,col].tolist()[:3]
            if pixel != [1,1,1]:
                bwMatrix[row,col] = 1

    #Split horizontally
    componentSeparationDfHorizontal = pd.DataFrame(bwMatrix[:,:,0].sum(axis=1),index=list(range(bwMatrix.shape[0])),columns=['Sample Pixel Number'])
    componentSeparationDfHorizontal.index.name = 'Row'
    rowBreakpoints = []
    for row in range(1,componentSeparationDfHorizontal.shape[0]-1):
        pixelNum = componentSeparationDfHorizontal.iloc[row,0]
        if (componentSeparationDfHorizontal.iloc[row-1,0] < occupancyCutoff and componentSeparationDfHorizontal.iloc[row,0] > occupancyCutoff) or (componentSeparationDfHorizontal.iloc[row,0] > occupancyCutoff and componentSeparationDfHorizontal.iloc[row+1,0] < occupancyCutoff):
            rowBreakpoints.append(row)

    #Split vertically
    componentSeparationDf = pd.DataFrame(bwMatrix[:,:,0].sum(axis=0),index=list(range(bwMatrix.shape[1])),columns=['Sample Pixel Number'])
    componentSeparationDf.index.name = 'Column'
    columnBreakpoints = []
    for row in range(1,componentSeparationDf.shape[0]-1):
        pixelNum = componentSeparationDf.iloc[row,0]
        if (componentSeparationDf.iloc[row-1,0] < occupancyCutoff and componentSeparationDf.iloc[row,0] > occupancyCutoff) or (componentSeparationDf.iloc[row,0] > occupancyCutoff and componentSeparationDf.iloc[row+1,0] < occupancyCutoff):
            columnBreakpoints.append(row)
    
    #Split off colorbar
    rgbScale = luminescent[:,columnBreakpoints[2]:columnBreakpoints[3]+1,:]
    colorBarRowIndices,colorBarColumnIndices = [],[]
    for i in range(rgbScale.shape[0]): # for every pixel:
        for j in range(rgbScale.shape[1]):
            pixel = rgbScale[i,j].tolist()[:3]
            if len(np.unique(pixel)) == 1 and np.unique(pixel) in [0,1]:
                pass
            else:
                colorBarRowIndices.append(i)
                colorBarColumnIndices.append(j)
    
    if rowBreakpoints[0] > headerCutoff:
        interval = 596
    else:
        interval = 706
    #BANDAID SOLUTION; FIND OUT WHY VERTICAL LUMINESCENT IMAGE SPLITTING VARIES SO MUCH
    if rowBreakpoints[-1] - rowBreakpoints[-2] != interval:
      if luminescent.shape[0] >= rowBreakpoints[-2]+interval:
        rowBreakpoints[-1] = rowBreakpoints[-2]+interval
      else:
        rowBreakpoints[-2] = rowBreakpoints[-2]-((rowBreakpoints[-2]+interval)-luminescent.shape[0])
        rowBreakpoints[-1] = rowBreakpoints[-2]+interval
    if columnBreakpoints[1] - columnBreakpoints[0] != interval:
      #print(columnBreakpoints)
      columnBreakpoints[1] = columnBreakpoints[0]+interval
    colorBar = rgbScale[min(colorBarRowIndices):max(colorBarRowIndices)+1,min(colorBarColumnIndices):max(colorBarColumnIndices)+1,:]
    miceSamples = luminescent[rowBreakpoints[-2]:rowBreakpoints[-1],columnBreakpoints[0]:columnBreakpoints[1],:]
    legend = luminescent[max(colorBarRowIndices):,columnBreakpoints[2]:]
    colorBarScale = luminescent[min(colorBarRowIndices):max(colorBarRowIndices)+1,columnBreakpoints[2]+max(colorBarColumnIndices)+1:,:]
    
    if visualize:
        sns.relplot(data=componentSeparationDfHorizontal,x='Row',y='Sample Pixel Number',kind='line',aspect=luminescent.shape[1]/luminescent.shape[0])
        sns.relplot(data=componentSeparationDf,x='Column',y='Sample Pixel Number',kind='line',aspect=luminescent.shape[1]/luminescent.shape[0])
    
    return miceSamples,colorBar,legend,colorBarScale

def ecdf(xdata):
    xdataecdf = np.sort(xdata)
    ydataecdf = np.arange(1, len(xdata) + 1) / len(xdata)
    return xdataecdf, ydataecdf

def findBrightfieldCutoff(brightfield,visualize=False):

    brightfieldDf = pd.DataFrame(brightfield)
    brightfieldDf.index.name = 'Row'
    brightfieldDf.columns.name = 'Column'
    plottingDf = brightfieldDf.stack().to_frame('Intensity')

    cutoff = 3.415974411376566
    x,y = ecdf(plottingDf['Intensity'])
    ecdfDf = pd.DataFrame(np.vstack([x,y]).T,columns=['Intensity','Proportion'])    
    ##Very bright image
    if ecdfDf[ecdfDf['Proportion'] >= 0.9].iloc[0,0] > 4500:
        #print(plottingDf.max())
        #logDf = np.log10(plottingDf)
        #scalingValLog = np.log10(ecdfDf[ecdfDf['Proportion'] >= 0.8].iloc[0,-2])
        #logDf = logDf+(cutoff-scalingValLog)
        #plottingDf = np.power(10,logDf)  
        dfToTransform = plottingDf.copy()
        transformedDfList = []
        for percentile in range(0,101,4):
            percentileVal2 = np.percentile(dfToTransform,percentile)
            if percentile == 0:
                vals2 = dfToTransform[dfToTransform['Intensity'] <= percentileVal2]
            else:
                vals2 = dfToTransform[(dfToTransform['Intensity'] <= percentileVal2) & (dfToTransform['Intensity'] > previousPercentileVal2)]
    
            previousPercentileVal2 = percentileVal2
        
            scaleFactor = vals2.mean().values[0]-referencePercentiles[percentile]
            scaledVals = np.subtract(vals2,scaleFactor)
            transformedDfList.append(scaledVals)
        plottingDf = pd.concat(transformedDfList).sort_values(['Row','Column'])
        #print(plottingDf.max())
        #sys.exit(0)

    visualBrightfieldMatrix = MinMaxScaler(feature_range=(11000,65000)).fit_transform(np.clip(plottingDf.values,a_min=0,a_max=5500))

    hist,bins = np.histogram(plottingDf.values,bins='auto', density=True)
    hist = savgol_filter(hist,7,2)
    maxHist = np.argmax(hist)
    elbow = maxHist+1000
    if visualize:
        g = sns.displot(data=plottingDf,x='Intensity',element='poly')
        g.axes.flat[0].axvline(x=elbow,linestyle=':',color='k')
        blackpointDf = plottingDf.copy()
        blackpointDf.loc[:,:] = visualBrightfieldMatrix
        blackpointDf2 = plottingDf.copy()
        g = sns.displot(data=pd.concat([blackpointDf,blackpointDf2],keys=['Yes','No'],names=['Scaled']),hue='Scaled',kind='hist',x='Intensity',element='poly',fill=False)
        g.set(yscale='log')

    return elbow,visualBrightfieldMatrix.reshape(brightfield.shape)

def rescaleBrightfieldImage(brightfield,brightfield2,luminescentSamples,visualize=False):
    
    rescaledBrightfieldMatrix = cv2.resize(brightfield, dsize=luminescentSamples.shape[:2])
    
    if np.mean(rescaledBrightfieldMatrix) > 10000:
        brightfieldCutoff = 90
        visualBrightfieldMatrix = cv2.resize(brightfield2, dsize=luminescentSamples.shape[:2])
        mouseBrightfieldMatrix = (visualBrightfieldMatrix[:,:,0] > brightfieldCutoff).astype(int)
    else:        
        brightfieldCutoff,visualBrightfieldMatrix = findBrightfieldCutoff(rescaledBrightfieldMatrix,visualize=visualize)
        mouseBrightfieldMatrix = (rescaledBrightfieldMatrix > brightfieldCutoff).astype(int)
    
    if visualize:
        fig = plt.figure()
        sns.heatmap(mouseBrightfieldMatrix,cmap='Greys')
    
    return mouseBrightfieldMatrix,visualBrightfieldMatrix

def horizontallySeparateMice(brightfieldSamples,visualize=False):
    brightfieldDf = pd.DataFrame(brightfieldSamples,index=list(range(brightfieldSamples.shape[0])),columns=list(range(brightfieldSamples.shape[1])))
    brightfieldDf.index.name = 'Row'
    brightfieldDf.columns.name = 'Column'
    brightfieldDf = brightfieldDf.sum(axis=1).to_frame('Count')
    brightfieldDf.loc[:,:] = MinMaxScaler().fit_transform(brightfieldDf.values)

    maxPointRangeCutoff = 0.4
    rangeBreakpoints = []
    for row in range(brightfieldDf.shape[0]-1,-1,-1):
        if brightfieldDf.iloc[row,0] > maxPointRangeCutoff:
            rangeBreakpoints.append(row)
            break        
    for row in range(rangeBreakpoints[0]-1,-1,-1):
        if brightfieldDf.iloc[row,0] < maxPointRangeCutoff:
            rangeBreakpoints.append(row)
            break        
    
    maxPoint = np.argmax(brightfieldDf.iloc[rangeBreakpoints[1]:rangeBreakpoints[0],0]) + rangeBreakpoints[1]
    breakpoints = [0,brightfieldDf.shape[0]-1]

    cutOff = maxPointRangeCutoff/2
    for row in range(maxPoint,-1,-1):
        if brightfieldDf.iloc[row,0] < cutOff:
            breakpoints[0] = row
            break        
    for row in range(maxPoint,brightfieldDf.shape[0]):
        if brightfieldDf.iloc[row,0] < 0.01:
            breakpoints[1] = row
            break        

    if visualize:
        g = sns.relplot(data=brightfieldDf,x='Row',y='Count',kind='line')
        g.axes.flat[0].axhline(y=maxPointRangeCutoff,linestyle=':',color='k')
        g.axes.flat[0].axhline(y=cutOff,linestyle=':',color='r')
        for breakpoint in breakpoints:
            g.axes.flat[0].axvline(x=breakpoint,linestyle=':',color='k')
        g.axes.flat[0].plot(maxPoint, brightfieldDf.iloc[maxPoint,0],color='k',marker='o')

    return breakpoints

def verticallySeparateMice(mouseBrightfieldMatrix,breakpoints,visualize=False):
   
    
    croppedBrightfieldMatrix = mouseBrightfieldMatrix[breakpoints[0]:breakpoints[1]+1,:]
    verticalMouseSeparationDf = pd.DataFrame(croppedBrightfieldMatrix,index=list(range(croppedBrightfieldMatrix.shape[0])),columns=list(range(croppedBrightfieldMatrix.shape[1])))
    verticalMouseSeparationDf.index.name = 'Row'
    verticalMouseSeparationDf.columns.name = 'Column'
    verticalMouseSeparationDf = verticalMouseSeparationDf.sum(axis=0).to_frame('Count').rolling(window=25).mean().fillna(value=0)
    verticalMouseSeparationDf.loc[:,:] = MinMaxScaler().fit_transform(verticalMouseSeparationDf.values)

    data = savgol_filter(verticalMouseSeparationDf.values.flatten(),31,2)
    data = abs(data)
    mins, _ = find_peaks(-1*data)
    #Further selection; mice have to be a certain distance apart
    trueMins = []
    minMouseWidth = 80
    minGroups = get_blocks(mins,minMouseWidth)
    for group in minGroups:
        if len(group) == 1:
            minIndex = group[0]
        else:
            dataVals = [data[x] for x in group]
            #minIndex = sorted(group)[-1]
            minIndex = group[dataVals.index(min(dataVals))]
        trueMins.append(minIndex)
    trueMins.append(verticalMouseSeparationDf.shape[0]-1)
    trueMins = np.unique(trueMins).tolist()
    #Even further selection; each interval must have a max of at least 15% the overall max
    splitMice = []
    maxCutoff = 0.2
    keptIntervals = []
    trueMins2 = []
    for i,trueMin in enumerate(trueMins[:-1]):
        maxI = 10
        if trueMin+maxI > verticalMouseSeparationDf.shape[0]-1:
            maxI = verticalMouseSeparationDf.shape[0]-trueMin-1
        if data[trueMin+maxI] >= data[trueMin]:
            trueMins2.append(trueMin)
    if data[trueMins[-1]-10] >= data[trueMins[-1]]:
        trueMins2.append(trueMins[-1])
    trueMins = trueMins2
    trueCutoff = min(data) + maxCutoff * (max(data)-min(data))
    for interval in pairwise(trueMins):
        if max(data[interval[0]:interval[1]]) > trueCutoff and abs(interval[1] - interval[0]) >= minMouseWidth:
            keptIntervals.append(interval)

    peaks,finalKeptIntervals = [],[]
    
    scaledInvervalValues = MinMaxScaler().fit_transform
    secondaryCutoff = 0.1
    for interval in keptIntervals:
        startpoint = interval[0]
        endpoint = interval[1]
        intervalValues = verticalMouseSeparationDf.query("Column > @startpoint and Column < @endpoint").reset_index()
        peakPoint = np.argmax(intervalValues['Count'].values)
        peak = intervalValues['Column'][peakPoint]
        peaks.append(peak)
        #Even further selection; crop sides of interval at cutoff point; starting from max point
        leftEndpoint = interval[0]
        rightEndpoint = interval[1]
        for val in range(peak,rightEndpoint):
            if intervalValues.query("Column == @val")['Count'].values[0] < secondaryCutoff:
                rightEndpoint = val
                break
        for val in range(peak,leftEndpoint,-1):
            if intervalValues.query("Column == @val")['Count'].values[0] < secondaryCutoff:
                leftEndpoint = val
                break
        finalKeptIntervals.append([leftEndpoint,rightEndpoint])
    
    #Scale peaks by image width to keep peaks tightly clustered between images
    minPlot = min(verticalMouseSeparationDf.index.get_level_values('Column').tolist())
    maxPlot = max(verticalMouseSeparationDf.index.get_level_values('Column').tolist())
    peaks = [(x-minPlot)/(maxPlot-minPlot) for x in peaks]

    #start = min(finalKeptIntervals[0][0],100)
    #end = max(finalKeptIntervals[-1][-1],600)
    #numMice = 5
    #distance = (end-start)/numMice

    #positionIntervals = [[start+distance*i,start+distance*(i+1)] for i in range(numMice)]
    #positionList,peakList = [],[]
    #for i,keptInterval in enumerate(finalKeptIntervals):
    #    ki0 = keptInterval[0]
    #    ki1 = keptInterval[1]
    #    percentMax = 0
    #    position = 0
    #    for j,positionInterval in enumerate(positionIntervals):
    #        pi0 = positionInterval[0]
    #        pi1 = positionInterval[1]
    #        intervalDf = verticalMouseSeparationDf.query("Column > @ki0 and Column <= @ki1")
    #        overallCount = intervalDf.sum().values[0]
    #        withinPositionCount = intervalDf.query("Column > @pi0 and Column <= @pi1").sum().values[0]
    #        percentInInterval = withinPositionCount/overallCount
    #        if percentInInterval > percentMax:
    #            position = j+1
    #            percentMax = percentInInterval
    #    peak = (positionIntervals[position-1][0]+positionIntervals[position-1][1])/2
    #    positionList.append(position)
    #    peakList.append(peak)
    
    
    if visualize:
        verticalMouseSeparationDf.loc[:,:] = data.reshape(-1,1)

        g = sns.relplot(data=verticalMouseSeparationDf,x='Column',y='Count',kind='line')
        g.axes.flat[0].axhline(y=trueCutoff,linestyle=':',color='k')
        g.axes.flat[0].axhline(y=secondaryCutoff,linestyle=':',color='r')
        #for i,interval in enumerate(finalKeptIntervals):
        for interval in finalKeptIntervals:
            g.axes.flat[0].axvline(x=interval[0],linestyle=':',color='k')
            g.axes.flat[0].axvline(x=interval[1],linestyle=':',color='k')
        #    g.axes.flat[0].annotate(str(positionList[i]),xy=(peakList[i]+1,0.95),color='r')
        #g.axes.flat[0].axhline(y=trueCutoff,linestyle=':',color='k')
        #g.axes.flat[0].axhline(y=secondaryCutoff,linestyle=':',color='r')
    #sys.exit(0)
    return finalKeptIntervals,peaks
    #return finalKeptIntervals,[x/6 for x in positionList]

def fullySeparateMice(luminescentSamples,brightfieldSamples,originalBrightfieldSamples,verticalBreakpoints,horizontalBreakpoints,visualize=False):
    
    miceSamples = np.dstack([luminescentSamples,brightfieldSamples])
    splitMice,splitBrightfields = [],[]
    posthocCutoff = 10
    for interval in verticalBreakpoints:
        splitMouse = miceSamples[horizontalBreakpoints[0]:horizontalBreakpoints[1],max(interval[0]-posthocCutoff,0):interval[1]-posthocCutoff,:]
        if len(originalBrightfieldSamples.shape) > 2:
            splitBrightfield = originalBrightfieldSamples[horizontalBreakpoints[0]:horizontalBreakpoints[1],max(interval[0]-posthocCutoff,0):interval[1]-posthocCutoff,:]
        else:
            splitBrightfield = originalBrightfieldSamples[horizontalBreakpoints[0]:horizontalBreakpoints[1],max(interval[0]-posthocCutoff,0):interval[1]-posthocCutoff]            
        splitMice.append(splitMouse)
        splitBrightfields.append(splitBrightfield)
    if visualize:
        fig, axes = plt.subplots(2,len(splitMice),figsize=(2.5*len(splitMice),5))
        for i,sample in enumerate(splitMice):
            if len(splitMice) > 1:
                axes[0,i].set_title(str(i+1))
                axes[0,i].imshow(sample[:,:,:3])
                axes[1,i].imshow(sample[:,:,3],cmap='Greys')
            else:
                axes[0].set_title(str(i+1))
                axes[0].imshow(sample[:,:,:3])
                axes[1].imshow(sample[:,:,3],cmap='Greys')
            if i == 0:
                if len(splitMice) > 1:
                    for ax in [axes[0,i],axes[1,i]]:
                        ax.set_xlabel('')
                        ax.set_xticks([])
                        ax.set_yticks([])
                        ax.spines['top'].set_visible(False)
                        ax.spines['right'].set_visible(False)
                        ax.spines['bottom'].set_visible(False)
                        ax.spines['left'].set_visible(False)                
                    axes[0,i].set_ylabel('Luminescent')
                    axes[1,i].set_ylabel('Brightfield')
                else:
                    for ax in [axes[0],axes[1]]:
                        ax.set_xlabel('')
                        ax.set_xticks([])
                        ax.set_yticks([])
                        ax.spines['top'].set_visible(False)
                        ax.spines['right'].set_visible(False)
                        ax.spines['bottom'].set_visible(False)
                        ax.spines['left'].set_visible(False)                
                    axes[0].set_ylabel('Luminescent')
                    axes[1].set_ylabel('Brightfield')
            else:
                if len(splitMice) > 1:
                    axes[0,i].axis('off')
                    axes[1,i].axis('off')
                else:
                    axes[0].axis('off')
                    axes[1].axis('off')

        fig.tight_layout()

    return splitMice,splitBrightfields

def returnRadianceMetrics(imageTitle,samples,splitBrightfields,colorScale,linearScale,trueMin,sampleNames=[],save_pixel_df=False,visualize=False):            
    outputDir = 'outputData/'
    statisticList = []
    if len(sampleNames) == 0:
        sampleNames = list(map(str,list(range(1,len(samples)+1))))

    radianceColorDict,pixelIntensityColorDict = {},{}
    for i,color in enumerate(colorScale):
        radianceColorDict[tuple(color)] = linearScale[i]
        pixelIntensityColorDict[tuple(color)] = i
    pixelDfList,pixelMatrixList,pixelMatrixNameList, = [],[],[]
    
    for sn,rgbSample in enumerate(samples):
        #Convert to RGB
        trueRGBSample = np.multiply(255,rgbSample[:,:,:3]).astype(int)
        #Create pixelwise radiance dataframe
        if visualize or save_pixel_df:
          intensityMatrix = img_array_to_single_val(trueRGBSample, pixelIntensityColorDict)
          radianceMatrix = img_array_to_single_val(trueRGBSample, radianceColorDict)
          brightfieldMatrix = rgbSample[:,:,3]
          if visualize:
              pixelIntensityDf = pd.DataFrame(intensityMatrix)
              pixelIntensityDf.index.name = 'Row'
              pixelIntensityDf.columns.name = 'Column'
              pixelRadianceDf = pd.DataFrame(radianceMatrix)
              pixelRadianceDf.index.name = 'Row'
              pixelRadianceDf.columns.name = 'Column'
              pixelBrightfieldDf = pd.DataFrame()
              pixelBrightfieldDf.index.name = 'Row'
              pixelBrightfieldDf.columns.name = 'Column'
              pixelRadianceAndBrightfieldDf = pd.concat([pixelIntensityDf.stack(),pixelRadianceDf.stack(),pixelBrightfieldDf.stack()],axis=1,keys=['Intensity','Radiance','Brightfield'])
              pixelDfList.append(pixelRadianceAndBrightfieldDf)
          else:
           imageMatrixPath = outputDir+'imageMatrices/'
           np.save(imageMatrixPath+'-'.join([imageTitle,sampleNames[sn]]),np.dstack([radianceMatrix,brightfieldMatrix,splitBrightfields[sn]]))
           with open(imageMatrixPath+'-'.join([imageTitle,sampleNames[sn]])+'.pkl','wb') as f:
               pickle.dump([trueMin,linearScale[-1]],f)

#             pixelMatrixList.append(np.dstack([radianceMatrix,brightfieldMatrix,splitBrightfields[sn]]))
#             pixelMatrixNameList.append('-'.join([imageTitle,sampleNames[sn]]))

        #Remove non mouse pixels
        brightfieldMask = rgbSample[:,:,3] == 1
        trueRGBSample = trueRGBSample[brightfieldMask]
        
        #Convert pixel intensity arrays to radiance arrays
        trueRGBSample = trueRGBSample[:,np.newaxis,:]
        scoringMatrix = img_array_to_single_val(trueRGBSample, pixelIntensityColorDict)
        radianceMatrix = img_array_to_single_val(trueRGBSample, radianceColorDict)

        #Selects non color scale pixels
        colorScaleBoolean = (radianceMatrix == -1).astype(int)
        additionMatrix = np.multiply(colorScaleBoolean,0) + colorScaleBoolean
                
        #Set mouse pixels (white/greyscale) to minimum detectable colorbar value
        radianceMatrix = np.add(radianceMatrix,additionMatrix)
        
        #Image statistics
        avgPixelIntensity = np.sum(scoringMatrix+1)/(scoringMatrix.shape[0])
        numTumorPixels = radianceMatrix[radianceMatrix != 0].shape[0]
        
        #Radiance statistics
        avgRadiance = np.sum(radianceMatrix)/(trueRGBSample.shape[0])
        totalRadiance = np.sum(radianceMatrix)
        
        #Tumor spatial area statistics
        tumorAreaCovered = numTumorPixels/trueRGBSample.shape[0]
        
        statisticList.append([avgPixelIntensity,avgRadiance,totalRadiance,tumorAreaCovered])

    if visualize:
      pixelDf = pd.concat(pixelDfList,keys=sampleNames,names=['Sample'])
      if 'processedImages' not in os.listdir(outputDir):
        os.mkdir(outputDir+'processedImages')
    else:
      pixelDf = []
    statisticMatrix = np.matrix(statisticList)
    statisticDf = pd.DataFrame(statisticMatrix,index=sampleNames,columns=['Average Pixel Intensity','Average Radiance','Total Radiance','Tumor Fraction'])
    statisticDf.index.name = 'Sample'

    if visualize:
      intensityDf = pixelDf['Radiance'].unstack('Column')
      brightfieldDf = pixelDf['Brightfield'].unstack('Column')
      initialDf = np.add((intensityDf.values == -1).astype(int),(brightfieldDf.values == 0).astype(int))
      initialDf = (initialDf != 0).astype(int) 
      additionDf = np.multiply(initialDf,trueMin-1)
      intensityDf.iloc[:,:] = np.multiply(intensityDf.values,1-initialDf) + additionDf
      numSamples = len(intensityDf.index.unique('Sample'))
      fig, axes = plt.subplots(1,numSamples,figsize=(2.5*numSamples,5))
      fig.subplots_adjust(right=0.8)
      cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])
      for i,sample in enumerate(intensityDf.index.unique('Sample')):
        b = splitBrightfields[i]
        sampleDf = intensityDf.query("Sample == @sample").dropna(axis=1) 
        cmap = sns.color_palette("magma", as_cmap=True)
        sampleDf.iloc[-1,-1] = np.nanmax(linearScale[-1])
        if len(intensityDf.index.unique('Sample')) > 1:
            g = sns.heatmap(sampleDf,cmap=transparent_cmap(cmap),cbar= i == 0,ax=axes[i],norm=matplotlib.colors.LogNorm(),vmin=np.nanmin(intensityDf.values),vmax=linearScale[-1],cbar_ax=cbar_ax,cbar_kws={'label':'Radiance\n(p/sec/cm$^2$/sr)'})
            axes[i].set_title('Sample '+str(i+1))
            axes[i].imshow(b,zorder=0, cmap='gray')
            axes[i].axis('off')
        else:
            g = sns.heatmap(sampleDf,cmap=transparent_cmap(cmap),cbar= i == 0,ax=axes,norm=matplotlib.colors.LogNorm(),vmin=np.nanmin(intensityDf.values),vmax=linearScale[-1],cbar_ax=cbar_ax,cbar_kws={'label':'Radiance\n(p/sec/cm$^2$/sr)'})
            axes.set_title('Sample '+str(i+1))
            axes.imshow(b,zorder=0, cmap='gray')
            axes.axis('off')
            
            
      fig.suptitle(imageTitle)
      fig.subplots_adjust(top=0.85)
      fig.savefig(outputDir+'processedImages'+imageTitle+'.png',bbox_inches='tight')
      plt.close()
    
    return statisticDf

def processGroupedMouseImage(imageTitle,luminescent,brightfield,brightfield2,visualize=False,save_pixel_df=False,sampleNames = [],save_images=False,cbar_lim=[]):
    
    #Preprocess images
    luminescentSamples,colorBar,legend,colorBarScale = returnLuminescentImageComponents(luminescent,visualize=visualize)
    
    colorScale = returnColorScale(colorBar)
    linearScale,trueMin = returnColorScaleSpan(legend,colorScale,colorBarScale,cbar_lim=cbar_lim)
    brightfieldSamples,originalBrightfieldSamples = rescaleBrightfieldImage(brightfield,brightfield2,luminescentSamples,visualize=visualize)

    #Crop images
    horizontalBreakpoints = horizontallySeparateMice(brightfieldSamples,visualize=visualize)
    verticalBreakpoints,peaks = verticallySeparateMice(brightfieldSamples,horizontalBreakpoints,visualize=visualize)    
    splitMice,splitBrightfields = fullySeparateMice(luminescentSamples,brightfieldSamples,originalBrightfieldSamples,verticalBreakpoints,horizontalBreakpoints,visualize=visualize)
    
    #Create radiance statistic dataframe and pixel-wise radiance dataframe
    radianceStatisticDf = returnRadianceMetrics(imageTitle,splitMice,splitBrightfields,colorScale,linearScale,trueMin,sampleNames = sampleNames,save_pixel_df=save_pixel_df,visualize=save_images)
    return radianceStatisticDf,peaks

def addTrueIndexToDataframe(radianceStatisticDf,sampleNameFile):
    matrixList,tupleList = [],[]
    for row in range(sampleNameFile.shape[0]):
        sampleName = list(sampleNameFile['Group'])[row]
        time = list(sampleNameFile['Day'])[row]
        sampleStatistics = radianceStatisticDf.xs((sampleName,time),level=('Group','Day'))
        matrixList.append(sampleStatistics.values)
        for sample in sampleStatistics.index.unique('Sample'):
          tupleList.append(sampleNameFile.iloc[row,:].values.tolist()+[sample])

    fullMatrix = np.vstack(matrixList)
    multiIndex = pd.MultiIndex.from_tuples(tupleList,names=list(sampleNameFile.columns)+['Sample'])#.droplevel('Group')
    completeDf = pd.DataFrame(fullMatrix,index=multiIndex,columns=radianceStatisticDf.columns)
    if 'SampleNames' in completeDf.index.names:
        completeDf = completeDf.droplevel('SampleNames')
    return completeDf

def addTrueIndexToPixelDataframe(radiancePixelDf,sampleNameFile):
    matrixList,tupleList = [],[]
    for row in range(sampleNameFile.shape[0]):
        sampleName = list(sampleNameFile['Group'])[row]
        time = list(sampleNameFile['Day'])[row]
        sampleStatistics = radiancePixelDf.xs((sampleName,time),level=('Group','Day'))
        matrixList.append(sampleStatistics.values)
        for sample in sampleStatistics.index.unique('Sample'):
          sampleDf = sampleStatistics.query("Sample == @sample").reset_index()
          for i in range(sampleDf.shape[0]):
            tupleList.append(sampleNameFile.iloc[row,:].values.tolist()+[sample,sampleDf['Row'][i],sampleDf['Column'][i]])

    fullMatrix = np.vstack(matrixList)
    multiIndex = pd.MultiIndex.from_tuples(tupleList,names=list(sampleNameFile.columns)+['Sample','Row','Column']).droplevel('Group')
    completeDf = pd.DataFrame(fullMatrix,index=multiIndex,columns=radiancePixelDf.columns)
    if 'SampleNames' in completeDf.index.names:
        completeDf = completeDf.droplevel('SampleNames')
    return completeDf

def luminescentBrightfieldMatchCheck(sampleNameFile,save_pixel_df=False):
  
  inputDir = 'inputData/'
  outputDir = 'outputData/'
  days = [x for x in pd.unique(sampleNameFile['Day'])]

  unmatchedGroups = []
  if save_pixel_df:
    if 'imageMatrices' not in os.listdir(outputDir):
      os.mkdir(outputDir+'imageMatrices')    

  for i in range(len(days)):
      day = days[i]
      tempDf = sampleNameFile.query("Day == @day")
      groups = list(pd.unique([x for x in pd.unique(tempDf['Group'])]))
      luminescentImages = [x.split('.')[0][0] for x in os.listdir(inputDir+'luminescent/'+day+'/') if '.DS' not in x]
      brightfieldImages = [x.split('.')[0][0] for x in os.listdir(inputDir+'brightfield/'+day+'/') if '.DS' not in x]
      for j in range(len(groups)):
          group = groups[j]
          if group not in luminescentImages or group not in brightfieldImages:
            if group not in luminescentImages:
              unmatchedGroups.append('luminescent/'+day+'/'+group)
            else:
              unmatchedGroups.append('brightfield/'+day+'/'+group)
  return unmatchedGroups

def amendSampleNames(fullDf,allPeaks,sampleNameFile,fullSplitGroupDict,save_pixel_df=False):
    base_dir = 'outputData/'

    clusterer = hdbscan.HDBSCAN(min_cluster_size=int(len(allPeaks)*0.1))
    cluster_labels = clusterer.fit_predict(np.array(allPeaks).reshape(-1,1))
    cluster_labels = [str(x+1) for x in cluster_labels]
    tempDf = pd.DataFrame({'Max':allPeaks,'Cluster':cluster_labels})
    sortedClusterList = tempDf.groupby(['Cluster']).median().sort_values(by='Max').index.get_level_values('Cluster').tolist()

    topX = 5
    topXclusters = tempDf.groupby(['Cluster']).count().sort_values(by=['Max'],ascending=False).index.get_level_values('Cluster').tolist()[:topX]
    allClusterMeansDf = tempDf.groupby(['Cluster']).median()
    clusterMeans = sorted([allClusterMeansDf.loc[x].values[0] for x in topXclusters])
    partitions = [0] + [(clusterMeans[x]+clusterMeans[x+1])/2 for x in range(len(clusterMeans)-1)] + [np.max(tempDf['Max'])]
    new_cluster_labels = []
    for row in range(tempDf.shape[0]):
        val = tempDf['Max'][row]
        for i in range(len(partitions)-1):
            if val > partitions[i] and val <= partitions[i+1]:
                new_cluster_labels.append(str(i+1))
                break

    tempDf['Cluster'] = new_cluster_labels
    #new_cluster_labels = [str(sortedClusterList.index(x)+1) for x in cluster_labels]

    newFullDf = fullDf.copy()
    newFullDf.index.names = ['Position' if x == 'Sample' else x for x in fullDf.index.names]
    newFullDf = newFullDf.assign(Sample=new_cluster_labels).set_index('Sample', append=True)
    #newFullDf['Max'] = tempDf['Max']

    #Make sure each 5 mouse group has 5 unique samples. If not, order by maxPeak
    indexingDf = newFullDf.droplevel('Sample')
    indexingDf = indexingDf.query("Position == '1'").droplevel('Position')
    subsetDfList = []
    allSplitGroupCombos = [[x.split(',,')[0],x.split(',,')[1][0]] for x in list(fullSplitGroupDict.keys())]
    for row in range(indexingDf.shape[0]):
        name = indexingDf.iloc[row,:].name
        subsetDf = newFullDf.xs(name,level=tuple(indexingDf.index.names),drop_level=False).reset_index()
        #Not a split group
        if name[0:2] not in allSplitGroupCombos:
            if subsetDf.shape[0] == 5 and len(list(pd.unique(subsetDf['Sample']))) != 5:
                subsetDf['Sample'] = subsetDf['Position']
        subsetDf = subsetDf.set_index(newFullDf.index.names)
        subsetDfList.append(subsetDf)
    #Combine sorted 5-mouse dfs (and others)
    newFullDf = pd.concat(subsetDfList)

    fullDfList = []
    splitGroups = [',,'.join(x.split(',,')[:2]) for x in fullSplitGroupDict]
    splitGroups = [x[:-1] for x in splitGroups]
    matrixRenamingDict = {}
    for currentDay in newFullDf.index.unique('Day'):
        dayDf = newFullDf.query("Day == @currentDay")
        for currentGroup in dayDf.index.unique('Group'):
            indexingKey = ',,'.join([currentDay,currentGroup])
            if indexingKey in splitGroups:
                keys = []
                for index,elem in enumerate(splitGroups):
                    if elem == indexingKey:
                        keys.append(list(fullSplitGroupDict.keys())[index])
                if type(keys) == str:
                    keys = [keys]
                subsetDfList = []
                splitPositionDict = {}
                for key in keys:
                    splitPositionDict[key.split(',,')[2]] = 0
                for key in keys:
                    splitKey = key.split(',,')
                    day,originalGroup,samples = splitKey[0],splitKey[1],splitKey[2].split(',')
                    group = originalGroup[:-1]
                    renamingPositions = fullSplitGroupDict[key]
                    subsetDf = newFullDf.query("Day == @day and Group == @group and Position == @samples").query("Sample == @renamingPositions")
                    for position,renamedPosition in zip(subsetDf.index.unique('Position'),renamingPositions):
                        splitPositionDict[splitKey[2]]+=1
                        trueIndex = newFullDf.query("Day == @day and Group == @group and Position == @samples").index.unique('Sample').tolist().index(renamedPosition)
                        matrixRenamingDict['-'.join([currentDay,currentGroup,renamedPosition])] = '-'.join([currentDay,originalGroup+'_'+','.join(renamingPositions),str(trueIndex+1)])
                    subsetDfList.append(subsetDf)
                renamedEntry = pd.concat(subsetDfList).sort_values(by=['Sample'])
            else:
                renamedEntry = newFullDf.query("Day == @currentDay and Group == @currentGroup")
                for position,renamedPosition in zip(renamedEntry.index.unique('Position'),renamedEntry.index.unique('Sample')):
                    matrixRenamingDict['-'.join([currentDay,currentGroup,renamedPosition])] = '-'.join([currentDay,currentGroup,position])
            if 'SampleNames' in sampleNameFile.columns:
                sampleNameVal = sampleNameFile[(sampleNameFile["Day"] == currentDay) & (sampleNameFile["Group"] == currentGroup)]['SampleNames'].values[0]
                if not pd.isna(sampleNameVal) and sampleNameVal != '':
                    renamingDict = {}
                    for oldSampleName,newSampleName in zip(renamedEntry.index.unique('Sample').tolist(),sampleNameVal.split(',')):
                        renamingDict[oldSampleName] = newSampleName
                        oldSampleKey = matrixRenamingDict.pop('-'.join([currentDay,currentGroup,oldSampleName]))
                        matrixRenamingDict['-'.join([currentDay,currentGroup,newSampleName])] = oldSampleKey
                    renamedEntry = renamedEntry.rename(renamingDict,level='Sample')
            renamedEntry = renamedEntry.sort_values(by=['Sample']).droplevel('Position')
            fullDfList.append(renamedEntry)

    if save_pixel_df:
        savezDict,minScaleDict = {},{}
        for savezKey in matrixRenamingDict:
            oldFileName = matrixRenamingDict[savezKey]
            savezDict[savezKey] = np.load(base_dir+'imageMatrices/'+oldFileName+'.npy')
            minScaleDict[savezKey] = pickle.load(open(base_dir+'imageMatrices/'+oldFileName+'.pkl','rb'))

        #Save concatenated files
        experimentName = os.getcwd().split(dirSep)[-1]
        np.savez_compressed(base_dir+experimentName+'-pixel',**savezDict)
        with open(base_dir+experimentName+'-minScale.pkl','wb') as f:
            pickle.dump(minScaleDict,f)
        #Delete temporary directory
        #shutil.rmtree(base_dir+'imageMatrices/')

    fullDf = pd.concat(fullDfList)
    return fullDf

def checkSplitGroups(day,group,allPeaks,sampleNames=[],visualize=False,save_df=True,save_pixel_df=False,save_images=False,cbar_lim=[]):
    base_dir = 'inputData/'
    #Check if length of image file name is > 1 (more than just a letter) -> split group
    luminescentImages = sorted([x.split('.')[0] for x in os.listdir(base_dir+'luminescent/'+day+'/') if len(x.split('.')[0]) > 1 and group in x.split('.')[0]])
    brightfieldImages = sorted([x.split('.')[0] for x in os.listdir(base_dir+'brightfield/'+day+'/') if len(x.split('.')[0]) > 1 and group in x.split('.')[0]])

    splitGroupDict = {}
    if len(luminescentImages) >= 1:
        if set(luminescentImages) == set(brightfieldImages):
            groupDfList,groupPixelDfList,groupPeaksList = [],[],[]
            splitIndex = 0
            for splitLuminescentFileName in luminescentImages:
                #Read in luminescent image
                if splitLuminescentFileName+'.png' in os.listdir(base_dir+'luminescent/'+day):
                  fileName = base_dir+'luminescent/'+day+'/'+splitLuminescentFileName+'.png'
                else:
                  fileName = base_dir+'luminescent/'+day+'/'+splitLuminescentFileName+'.PNG'
                luminescent = mplImage.imread(fileName)[:,:,:3]

                #Read in brightfield image
                if splitLuminescentFileName+'.tif' in os.listdir(base_dir+'brightfield/'+day):
                  fileName = base_dir+'brightfield/'+day+'/'+splitLuminescentFileName+'.tif'
                else:
                  fileName = base_dir+'brightfield/'+day+'/'+splitLuminescentFileName+'.TIF'
                brightfield = mplImage.imread(fileName)
                brightfield2 = cv2.imread(fileName)
                positionsToKeep = splitLuminescentFileName[1:].split('_')[1].split(',')
                groupDf,groupPeaks = processGroupedMouseImage(day+'-'+splitLuminescentFileName,luminescent,brightfield,brightfield2,sampleNames=sampleNames,visualize=visualize,save_images=save_images,save_pixel_df=save_pixel_df,cbar_lim=cbar_lim)
                if splitIndex != 0:
                    originalSamples = groupDf.index.unique('Sample').tolist()
                    newSamples = [str(int(x)+splitIndex) for x in originalSamples]
                    renamingDict = {}
                    for og,new in zip(originalSamples,newSamples):
                        renamingDict[og] = new
                    groupDf = groupDf.rename(renamingDict,level='Sample')

                splitIndex+=len(groupDf.index.unique('Sample').tolist())
                splitGroupDict[day+',,'+splitLuminescentFileName.split('_')[0]+',,'+','.join(groupDf.index.unique('Sample').tolist())] = positionsToKeep
                print(splitGroupDict)
                #splitGroupDict[day+',,'+group+',,'+','.join(groupDf.index.unique('Sample').tolist())] = positionsToKeep
                groupDfList.append(groupDf)
                groupPeaksList+=groupPeaks
            groupDf = pd.concat(groupDfList)
            return groupDf,groupPeaksList,splitGroupDict
        else:
            print('These images are not shared:\n')
            for missingImage in list(set(luminescentImages) ^ set(brightfieldImages)):
              print(day+'-'+missingImage)
            print('\nExiting...')
            sys.exit(0)
    else:
        #Read in luminescent image
        if group+'.png' in os.listdir(base_dir+'luminescent/'+day):
          fileName = base_dir+'luminescent/'+day+'/'+group+'.png'
        else:
          fileName = base_dir+'luminescent/'+day+'/'+group+'.PNG'
        luminescent = mplImage.imread(fileName)[:,:,:3]

        #Read in brightfield image
        if group+'.tif' in os.listdir(base_dir+'brightfield/'+day):
          fileName = base_dir+'brightfield/'+day+'/'+group+'.tif'
        else:
          fileName = base_dir+'brightfield/'+day+'/'+group+'.TIF'
        brightfield = mplImage.imread(fileName)
        brightfield2 = cv2.imread(fileName)        
        groupDf,groupPeaks = processGroupedMouseImage(day+'-'+group,luminescent,brightfield,brightfield2,sampleNames=sampleNames,visualize=visualize,save_images=save_images,save_pixel_df=save_pixel_df,cbar_lim=cbar_lim)
        return groupDf,groupPeaks,splitGroupDict

def moveRawImages(sampleNameFile,pathToRawImages):
    fileExtensionDict = {'brightfield':'.TIF','luminescent':'.PNG'}
    dayRenamingDict = {}
    for imageType in ['brightfield','luminescent']:
        if imageType not in os.listdir('inputData'):
            os.mkdir('inputData/'+imageType)
        for day in list(pd.unique(sampleNameFile['Day'])):
            newDay = 'D'+''.join([i for i in day if i.isdigit()])
            dayRenamingDict[day] = newDay
            if day in os.listdir(pathToRawImages):
                if newDay not in os.listdir('inputData/'+imageType):
                    os.mkdir('inputData/'+imageType+'/'+newDay)
                for group in list(pd.unique(sampleNameFile['Group'])):
                    if group in os.listdir(pathToRawImages+'/'+day):
                        initialPath = pathToRawImages+'/'+day+'/'+group+'/'
                        if imageType == 'brightfield':
                            initialName = 'photograph.TIF'
                        else:
                            for fileName in os.listdir(pathToRawImages+'/'+day+'/'+group):
                                if '.png' in fileName or '.PNG' in fileName:
                                    initialName = fileName
                                    break
                        finalPath =  'inputData/'+imageType+'/'+newDay+'/'
                        finalName = group+fileExtensionDict[imageType]
                        shutil.copyfile(initialPath+initialName,finalPath+finalName)
    
    dayIndex = list(sampleNameFile.columns).index('Day')
    for i in range(sampleNameFile.shape[0]):
        oldDay = sampleNameFile.iloc[i,dayIndex]
        sampleNameFile.iloc[i,dayIndex] = dayRenamingDict[oldDay]
    return sampleNameFile

def fullInVivoImageProcessingPipeline_part1(sampleNameFile,visualize=False,save_df=True,save_pixel_df=False,save_images=False,pathToRawImages='',cbar_lim=[]):
  outputDir = 'outputData/'
  if pathToRawImages != '':
      sampleNameFile = moveRawImages(sampleNameFile,pathToRawImages)
  unmatchedGroups = luminescentBrightfieldMatchCheck(sampleNameFile,save_pixel_df=save_pixel_df)
  if len(unmatchedGroups) == 0:
    days = [x for x in pd.unique(sampleNameFile['Day'])]

    dayDfList,dayPixelDfList,dayPeaksList = [],[],[]
    fullSplitGroupDict = {}
    for i in trange(len(days), desc='Processing Days:'):
        day = days[i]
        groupDfList,groupPixelDfList = [],[]
        tempDf = sampleNameFile.query("Day == @day")
        groups = list(pd.unique([x for x in pd.unique(tempDf['Group'])]))
        #print(day)
        for j in trange(len(groups), desc='Processing Groups:',leave=False):
            group = groups[j]
            sampleNames = []
            
            groupDf,groupPeaks,splitGroupDict = checkSplitGroups(day,group,dayPeaksList,sampleNames=sampleNames,visualize=visualize,save_images=save_images,save_pixel_df=save_pixel_df,cbar_lim=cbar_lim)
            groupDfList.append(groupDf)
            dayPeaksList+=groupPeaks
            fullSplitGroupDict = {**fullSplitGroupDict,**splitGroupDict}
            #print(group)
        dayDf = pd.concat(groupDfList,keys=groups,names=['Group'])
        dayDfList.append(dayDf)

    experimentName = os.getcwd().split(dirSep)[-1]
    outputFileName = 'radianceStatisticPickleFile-'+experimentName
    if 'SampleNames' not in tempDf.columns:
        sampleNamesColumn = []
    else:
        sampleNamesColumn = sampleNameFile['SampleNames'].tolist()
    
    fullDf = pd.concat(dayDfList,keys=days,names=['Day'])
    fullDf = amendSampleNames(fullDf,dayPeaksList,sampleNameFile,fullSplitGroupDict,save_pixel_df=save_pixel_df)
    radianceStatisticDf = addTrueIndexToDataframe(fullDf,sampleNameFile)
    radianceStatisticDf['Time'] = [int(x[1:]) for x in radianceStatisticDf.index.get_level_values('Day').tolist()]
    radianceStatisticDf = radianceStatisticDf.set_index(['Time'],append=True)
    
    #Ensure order is "all group indices",day,time,sample
    allGroupIndices = [x for x in radianceStatisticDf.index.names if x not in ['Day','Time','Sample']]
    radianceStatisticDf = radianceStatisticDf.reset_index().set_index(allGroupIndices+['Day','Time','Sample'])

    if save_df:
      radianceStatisticDf.to_pickle(outputDir+outputFileName+'.pkl')
      radianceStatisticDf.to_excel(outputDir+outputFileName+'.xlsx')    
    return radianceStatisticDf
  else:
    print('These images are missing:\n')
    for missingImage in unmatchedGroups:
      print(missingImage)
    print('\nExiting...')
    return []

def fullInVivoImageProcessingPipeline_part2(radianceStatisticDf,save_df=True):
  # file location set up
  outputDir = 'outputData/'
  npz_dir = outputDir
  minScale_dir = outputDir
  experimentName = os.getcwd().split(dirSep)[-1]
  
  # additional processing
  full_df = generate_mouseIDs(radianceStatisticDf) # label with unique mouse IDs
  full_df = replace_background(full_df) # fix background values

  processed_df, maxWidth, maxHeight = merge_images(full_df, npz_dir, minScale_dir) # merge all mice images

  # save data
  if save_df:
    processed_df.to_pickle(outputDir+'radianceStatisticPickleFile_processed-'+experimentName+'.pkl')
    processed_df.to_excel(outputDir+'radianceStatisticPickleFile_processed-'+experimentName+'.xlsx')

  return processed_df, maxWidth, maxHeight


def generate_mouseIDs(radianceStatisticDf):
  '''
  Adds a unique mouse ID for each individual mouse.
  '''
  print('Adding unique mouse ID.')

  mouse_id = 0
  mouse_df_list = []
  # filter by experiment
  for exp in radianceStatisticDf.reset_index().ExperimentName.unique():
    exp_df = radianceStatisticDf.query('ExperimentName == @exp')
    for group in exp_df.reset_index().Group.unique():
      group_df = exp_df.query('Group == @group')

      # filter by time
      samples_list = []
      times_list = group_df.reset_index().Time.unique()
      for time in times_list:
        time_df = group_df.query('Time == @time')
        samples = time_df.reset_index().Sample
        samples_list.append(samples)

      # create dictionary of times and samples
      samples_at_times = dict(zip(times_list,samples_list))

      # samples on first day
      samples_at_start = samples_at_times[list(samples_at_times.keys())[0]]

      # mouse id generated from the mice on the first day of data for each group
      # create dictionary mapping the "sample" to the "mouse id"
      mouse_id_list = []
      for first_samples in samples_at_start:
        mouse_id = mouse_id + 1
        mouse_id_list.append(mouse_id)

      # print(list(samples_at_start))
      # print(mouse_id_list)
      mouse_labeling_dict = dict(zip(samples_at_start,mouse_id_list)) # dict that maps sample to mouseID
      # print(mouse_labeling_dict)
      for day in group_df.reset_index().Time.unique():
        # samples on current day
        current_samples = group_df.query('Time == @day').reset_index().Sample

        # print(day)
        # print(list(current_samples))
        # print(mouse_labeling_dict)

        # make sure don't have duplicates
        renaming_list = []
        if len(current_samples) == len(current_samples.unique()): # all sample names are unique
          # print('A')
          # print(day,current_samples.values)
          for sample in current_samples:
            current_mouse_id = mouse_labeling_dict[sample] # mouseID
            renaming_list.append(current_mouse_id)  # keep list of mouseID for this group/day
            # print('done')
          # print(renaming_list)
          # print('\n')

        else: # have some repeating sample names
          # print('B')
          # print(mouse_id_list)
          for i in range(0,len(current_samples)):
            sample = current_samples[i]
            current_mouse_id = mouse_id_list[i] # mouseID
            renaming_list.append(current_mouse_id)  # keep list of mouseID for this group/day
          # print(renaming_list)
          # print('\n')
      
        mouse_df = group_df.query('Time == @day')
        mouse_df['MouseID'] = renaming_list
        mouse_df_list.append(mouse_df)

  full_df = pd.concat(mouse_df_list).reset_index()

  # confirm all mice labeled correctly
  print('Need to correct the following mice:')
  counter = 0
  for mouse in full_df.reset_index().MouseID.unique():
    mouse_df = full_df.query('MouseID == @mouse')
    num_unique_samples = len(mouse_df.reset_index().Sample.unique())
    if num_unique_samples != 1:
      print(mouse)
      counter = counter + 1
  if counter==0:
    print('None. All mice correctly labeled.')

  return full_df

def replace_background(full_df):
  '''
  Make background values equal to 100
  '''
  # replace zero values and those below minimum detection per pixel of 100
  full_df['Average Radiance'] = full_df['Average Radiance'].apply(lambda x: 100 if x < 100 else x)

  return full_df

def get_npz_minScale_info(merged_data, npz_dir, minScale_dir):
  '''
  Function that generates dataframes with experiment and scale info for each image.

  Input:
  merged_data -- dataframe of merged .pkl files with mouse IDs (output of generate_mouseIDs() function)
  npz_dir -- path to the .npz files to merge
  minScale_dir -- path to the minScale.pkl files to merge

  Output:
  expList_npz -- list of experiment names
  labelDf_npz -- dataframe with experiment for each image
  labelDf_minScale -- dataframe with min and max scale for each image
  matrixList -- list of each image matrix
  '''
  # get the npz pixel file names
  filenameList_npz = sorted([x for x in os.listdir(npz_dir) if x.endswith('pixel.npz')])  # only keep the -pixel.npz files
  expList_npz = [f_npz.split('-')[1] for f_npz in filenameList_npz] # list of experiments

  # get the minScale file names
  filenameList_minScale = sorted([x for x in os.listdir(minScale_dir) if x.endswith('minScale.pkl')])  # only keep the -minScale.pkl files
  expList_minScale = [f_minScale.split('-')[1] for f_minScale in filenameList_minScale] # list of experiments

  # check that have same experiments
  if set(expList_npz) == set(expList_minScale): expList = expList_npz
  else: raise Exception('Error: Experiments for .npz and minScale.pkl files are not the same.')

  # load in each experiment
  labelListofLists_npz = []  # list of labels for each npz matrix
  matrixListofLists = []  # list that has each individual 3D matrix
  labelListofLists_minScale = []  # list of labels for each minScale file
  vminListofLists = []  # list of vmin values for each minScale file
  vmaxListofLists = []  # list of vmax values for each minScale file

  for file_npz, file_minScale in tqdm(zip(filenameList_npz, filenameList_minScale), total=len(filenameList_npz)):
    exp_npz = file_npz.split('-')[1]  # npz experiment name
    exp_minScale = file_minScale.split('-')[1]  # minScale experiment name
    try:
      if (exp_npz == exp_minScale) == True:  # make sure the experiment names are the same (in the same order)
        exp_name = exp_npz  # same as exp_minScale
        if exp_name in merged_data.reset_index().ExperimentName.unique():  # only merge files with data in original master dataframe
          # load in each npz experiment file
          selectionDict, selectionKeyDf, selectionTitle = loadNPZ(f'{npz_dir}/{file_npz}', groups='all', days='all', samples='all')
          labelListofLists_npz.append([f'{exp_name}-{x}' for x in list(selectionDict.keys())])  # append list of matrix labels (eg MP4-D3-A-1 (Experiment-Day-Group-Sample)) for that experiment
          matrixListofLists.append(list(selectionDict.values()))  # append list of matrices for that experiment
          
          # load in each minScale experiment file
          scaleDict = loadPickle(f'{minScale_dir}/{file_minScale}')  # dictionary with min/max scale for each image
          labelListofLists_minScale.append([f'{exp_name}-{x}' for x in list(scaleDict.keys())])  # append list of labels (eg MP4-D3-A-1 (Experiment-Day-Group-Sample)) for that experiment
          vminListofLists.append([sublist[0] for sublist in list(scaleDict.values())])
          vmaxListofLists.append([sublist[1] for sublist in list(scaleDict.values())])
        
      else:
        raise Exception
    except:
      print(f'Experiments not aligned: {exp_npz} {exp_minScale}')

  # indices for labelList_npz will match indices of matrixList
  labelList_npz = [label_npz for labelExpList_npz in labelListofLists_npz for label_npz in labelExpList_npz]  # list of each matrix label (flatten list of lists)
  matrixList = [matrix for matrixExpList in matrixListofLists for matrix in matrixExpList]  # list of each matrix (flatten list of lists)

  # indices for labelList_minScale will match indices of vminList and vmaxList
  labelList_minScale = [label_minScale for labelExpList_minScale in labelListofLists_minScale for label_minScale in labelExpList_minScale]  # list of each minScale label (flatten list of lists)
  vminList = [vmin for vminExpList in vminListofLists for vmin in vminExpList]  # list of each vmin (flatten list of lists)
  vmaxList = [vmax for vmaxExpList in vmaxListofLists for vmax in vmaxExpList]  # list of each vmax (flatten list of lists)

  # convert labelList_npz to dataframe
  exp_list = []
  day_list = []
  group_list = []
  mouse_list = []
  for label in labelList_npz:
    exp_list.append(label.split('-')[0])
    day_list.append(label.split('-')[1])
    group_list.append(label.split('-')[2])
    mouse_list.append(label.split('-')[3])

  labelDf_npz = pd.DataFrame(
      {'Experiment': exp_list,
       'Day': day_list,
       'Group': group_list,
       'Mouse': mouse_list
       })

  labelDf_npz['Index'] = labelDf_npz.index.values
  labelDf_npz = labelDf_npz.set_index(['Experiment', 'Day', 'Group', 'Mouse'])

  # convert labelList_minScale to dataframe
  exp_list = []
  day_list = []
  group_list = []
  mouse_list = []
  for label in labelList_minScale:
    exp_list.append(label.split('-')[0])
    day_list.append(label.split('-')[1])
    group_list.append(label.split('-')[2])
    mouse_list.append(label.split('-')[3])

  labelDf_minScale = pd.DataFrame(
      {'Experiment': exp_list,
       'Day': day_list,
       'Group': group_list,
       'Mouse': mouse_list,
       'vmin': vminList,
       'vmax': vmaxList,
       })

  labelDf_minScale = labelDf_minScale.set_index(['Experiment', 'Day', 'Group', 'Mouse'])

  return expList_npz, labelDf_npz, labelDf_minScale, matrixList

def add_metadata_to_images(expList_npz, merged_data, labelDf_newtime):
  '''
  Adds additional information about experiment to each image.
  '''
  good_exp_list = list(merged_data.reset_index().ExperimentName.unique())

  col_names = ['Group','CAR_Binding','CAR_Costimulatory','Tumor','TumorCellNumber','TCellNumber','bloodDonorID','Perturbation']
  drop_cols = ['Average Pixel Intensity','Average Radiance','Total Radiance','Tumor Fraction','Day','Time','Date','ExperimentName','Researcher']
  fullExpDf_list=[]
  # print(expList_npz,good_exp_list)
  for exp_name in expList_npz: # expList_npz same as expList_minScale
      if exp_name in merged_data.reset_index().ExperimentName.unique(): # only merge files with data in original master dataframe
          if exp_name in good_exp_list:
              try:
                  # get metadata for each group
                  exp_df_raw = merged_data.query('ExperimentName == @exp_name')
                  exp_df = exp_df_raw.reset_index().set_index(col_names).drop(drop_cols,axis=1).drop_duplicates()
                  group_data_list = list(exp_df.index.unique())

                  labelDf_exp = labelDf_newtime.query('Experiment == @exp_name')
                  idx=list(labelDf_newtime.index.names)

                  # get group names
                  group_names = labelDf_exp.reset_index().Group.unique()

                  # print(exp_name,len(group_data_list),len(group_names),exp_df_raw.shape[0],labelDf_exp.shape[0])
                  # print(group_names)

                  # add metadata to labelDf
                  group_df_list=[]
                  for i,group_name in enumerate(group_names): # for each group name
                      # group_df = labelDf.query('Experiment == @exp_name and Group == @group_name') # df for each group in each experiment
                      group_df = labelDf_exp.query('Group == @group_name') # df for each group in each experiment
                      # print(i,group_name,group_df.shape[0])
                      # combine/renumber groups to match order of corresponding data in group_data_list

                      #print(col_names)
                      for j,col in enumerate(col_names): # for each metadata type
                          # print(group_name,i,group_data_list[i])
                          if col != 'Group':
                            group_df[col] = group_data_list[i][j] # add new column (j) with metadata for corresponding group (i)
                      group_df_list.append(group_df)
                  labelExpDf = pd.concat(group_df_list) # combine the group dfs with the new metadata

                  ##### DEBUGGING ONLY #######
                  # labelExpDf.to_pickle(f'/Users/kenetal/Desktop/labelExpDf.pkl')
                  # exp_df_raw.to_pickle(f'/Users/kenetal/Desktop/exp_df_raw.pkl')
                  ##### DEBUGGING ONLY #######

                  # sort before merging
                  labelExpDf.sort_values(by=['Day','Mouse','Tumor','TCellNumber','Perturbation'],axis=0, inplace=True)
                  exp_df_raw.sort_values(by=['Day','Sample','Tumor','TCellNumber','Perturbation'],axis=0, inplace=True)

                  # add new metadata to old info
                  if (np.sum(labelExpDf.reset_index().Mouse != exp_df_raw.reset_index().Sample) + 
                      np.sum(labelExpDf.reset_index().Day != exp_df_raw.reset_index().Day) +
                      np.sum(labelExpDf.reset_index().CAR_Binding != exp_df_raw.reset_index().CAR_Binding) +
                      np.sum(labelExpDf.reset_index().CAR_Costimulatory != exp_df_raw.reset_index().CAR_Costimulatory) +
                      np.sum(labelExpDf.reset_index().Tumor != exp_df_raw.reset_index().Tumor) +
                      np.sum(labelExpDf.reset_index().TumorCellNumber != exp_df_raw.reset_index().TumorCellNumber) + 
                      np.sum(labelExpDf.reset_index().TCellNumber != exp_df_raw.reset_index().TCellNumber) + 
                      np.sum(labelExpDf.reset_index().bloodDonorID != exp_df_raw.reset_index().bloodDonorID) + 
                      np.sum(labelExpDf.reset_index().Perturbation != exp_df_raw.reset_index().Perturbation)
                    ) == 0: # double check that correctly lined up for merging
                      fullExpDf = pd.concat([labelExpDf.reset_index().rename(columns={'Index':'ImageID'}).drop(['Experiment','Mouse'],axis=1), # new
                                            exp_df_raw.reset_index().drop(['Group','CAR_Binding','CAR_Costimulatory', 'Tumor', 'TumorCellNumber', 'TCellNumber','bloodDonorID', 'Perturbation', 'Day'],axis=1)], # old
                                            axis=1)#.set_index(col_names)                                
                      fullExpDf_list.append(fullExpDf)
                  else:
                      print('ERROR: INFO FROM LABELDF DOES NOT MATCH WITH INFO FROM ORIGINAL MATRIX DATA')
                      raise Exception('ERROR: INFO FROM LABELDF DOES NOT MATCH WITH INFO FROM ORIGINAL MATRIX DATA')
              
              except:
                  print(exp_name)

  labelDf_all = pd.concat(fullExpDf_list).set_index(['Date','ExperimentName','Researcher','CAR_Binding','CAR_Costimulatory','Tumor','TumorCellNumber','TCellNumber','bloodDonorID','Perturbation','Group','Day','Time','Sample','MouseID','ImageID']).drop(['index'],axis=1,errors='ignore') # sometimes "index" appears as column -- drop it

  return labelDf_all

def crop_tail(matrix):
    '''
    Crops mouse tail from one image.
    Returns all dimensions of image matrix (radiance,mousePixel,brightfield)
    '''
    ## knee crop tail method ##
    # use brightfield, not mousePixel
    brightfield_df = pd.DataFrame(matrix[:,:,2])
    # brightfield_df = np.log10(brightfield_df)
    # brightfield_df = brightfield_df/max(brightfield_df.max())
    columnBrightfield = (brightfield_df.sum(axis=1)).to_frame('Value') # percent of pixels in row that are mousePixels
    maxVal = np.max(columnBrightfield).values[0] # find maximum value of brightfield
    maxIndex = np.argmax(columnBrightfield) # find row where maximum occurs

    # only look at x-vals after max and y-vals below threshold (i.e. bottom right quadrant)
    threshold = 0.8*maxVal
    try:
        start_idx = np.where((columnBrightfield[columnBrightfield.index > maxIndex] < threshold).Value.values)[0][0]+maxIndex
        # y-values of pixels within range
        pixels2search_vals = columnBrightfield[columnBrightfield.index > start_idx].Value.values
        # smooth the curve using Savitzky-Golay filter
        smoothed_pixels2search_vals = savgol_filter(pixels2search_vals, window_length=51, polyorder=2)
        # x-values (idx) of pixels within range
        pixels2search_idx = np.arange(len(pixels2search_vals)) + start_idx
        # knee finder method
        kl = KneeLocator(pixels2search_idx,smoothed_pixels2search_vals, curve='convex', direction='decreasing')
        # kl.plot_knee()
        knee_crop_idx = kl.knee # index to crop at
        matrix_tailcrop = matrix[:knee_crop_idx,:,:] # crop tail
    except: # no tail to crop
        matrix_tailcrop = matrix
        knee_crop_idx=np.nan
  
    # if matrix_tailcrop.shape[0] > 345: # should only be 2643 and 2645 which are messed up and will get fixed/ignored
    #     matrix_tailcrop = matrix_tailcrop[:345,:,:]
    #     print('Cropping at max height 345')
  
    return matrix_tailcrop

def padMatrix(oldMatrix,maxLength,maxWidth,paddingConstant,i):
  '''
  Adds padding to matrix. (0,0) is the top left.
  New matrix will have padding on all sides, if needed.
  If uneven padding, will add fewer to top and left. Bottom and right will have more padding.

  Inputs:
  oldMatrix -- m x n x i -- matrix to pad
  maxLength -- M         -- length of padded matrix
  maxWidth  -- N         -- width of padded matrix
  paddingConstant -- 1 x i -- values to use for padding in each dimension
  i -- dimension to pad 

  Output:
  newMatrix -- M x N x i -- padded matrix


  Ex:

  oldMatrix:
             array([[1., 1.],
                    [1., 1.],
                    [1., 1.],
                    [1., 1.],
                    [1., 1.]])


  pad with zeros to be size 8 x 5


  newMatrix:
             array([[0., 0., 0., 0., 0.],
                    [0., 1., 1., 0., 0.],
                    [0., 1., 1., 0., 0.],
                    [0., 1., 1., 0., 0.],
                    [0., 1., 1., 0., 0.],
                    [0., 1., 1., 0., 0.],
                    [0., 0., 0., 0., 0.],
                    [0., 0., 0., 0., 0.]])

  '''
  # create matrix of correct max dimensions with default pad values
  newMatrix = np.multiply(np.ones([maxLength,maxWidth]),paddingConstant)

  # get padding dimension values
  y_padding = (maxLength-oldMatrix.shape[0])/2
  start_y = int(np.floor(y_padding))
  end_y = int(maxLength-np.ceil(y_padding))

  x_padding = (maxWidth-oldMatrix.shape[1])/2
  start_x = int(np.floor(x_padding))
  end_x = int(maxWidth-np.ceil(x_padding))

  # add original values to correct location
  newMatrix[start_y:end_y,start_x:end_x] = oldMatrix[:,:,i]

  return newMatrix

def pad_images(matrix_rescaled_list,maxHeight,maxWidth):
  '''
  Pad each image (in all three dimensions) to be the same width (maxWidth).
  
  Inputs:
  matrix_rescaled_list -- list of image matrices to be rescaled
  maxHeight -- max height of all images
  maxWidth -- max width of all images
  
  Output:
  bigMatrix -- matrix of all images merged together after padding
  '''

  newMatrixList = []
  for matrix in tqdm(matrix_rescaled_list): # for each rescaled matrix
      dstackList = []
      for i,paddingConstant in enumerate([-999,0,np.min(matrix[:,:,2])]): # radiance,mousePixels,brightfield
          # padding function (shouldn't have any padding on height since already scaled to maxHeight)    
          newMatrix = padMatrix(matrix,maxHeight,maxWidth,paddingConstant,i) 
  #        # newMatrix = newMatrix[:,50:220] # crop extra space
          dstackList.append(newMatrix) # add each of i dimensions to list
      newMatrixList.append(np.dstack(dstackList)) # combine matrices along ith dimension and add to list
  print('Stacking Images (Warning: This step may take a few minutes.)')
  bigMatrix = np.stack(newMatrixList,axis=3) # combine each padded matrix (add 4th dimension -- (length,height,3layers,stack))

  return bigMatrix

def merge_images(merged_data, npz_dir, minScale_dir):
    '''
    Merge each individual mouse image (.npz files)
    '''
    print('Merging Images.')

    # get experiment and scale info for each image
    print('Getting information for each image')
    expList_npz, labelDf_npz, labelDf_minScale, matrixList = get_npz_minScale_info(merged_data, npz_dir, minScale_dir)

    # combine the data so that the vmin,vmax info matches each image index value
    labelDf_merged = labelDf_npz.copy()
    labelDf_merged.loc[:,labelDf_minScale.columns] = labelDf_minScale

    # which experiments have NaNs (missing info for min/max)
    print('Need to fix NaNs in:')
    print(labelDf_merged[labelDf_merged['vmin'].isna()].reset_index().Experiment.unique())
    
    # # rescale time to be zero on day of CAR administration
    # labelDf_newtime = prf.rescale_time(labelDf_merged)

    # add additional information about each experiment to dataframe
    print('Adding additional metatdata')
    labelDf_all = add_metadata_to_images(expList_npz, merged_data, labelDf_merged)
    labelDf_all.to_hdf(f'outputData/labelDf_all-{os.getcwd().split(dirSep)[-1]}.hdf',key='df',mode='w')
    print('Dataframe with metadata saved.')
    
    # tail cropping
    print('Performing tail cropping')
    matrix_tailCrop_list = [crop_tail(x) for x in tqdm(matrixList)] # crop tails from each image in matrixList

    # rescale images
    print('Rescaling images to same height')
    maxHeight = max([x.shape[0] for i,x in enumerate(matrix_tailCrop_list)]) # 345 -- get max height to rescale all images to
    matrix_rescaled_list = [imutils.resize(x, height=maxHeight, inter=cv2.INTER_LINEAR) for x in tqdm(matrix_tailCrop_list)] # rescale each image to maxHeight while keeping aspect ratio the same

    # find slanted mice
    print('Finding slanted images')
    # get slope/angle of each mouse
    thresh=7 # degrees ## TODO -- make this part of GUI
    angle_list = []
    for i,matrix in tqdm(enumerate(matrix_tailCrop_list),total=len(matrix_tailCrop_list)):
        # OLS regression on mouse coordinates -- flip mouse to make work better
        y = np.where(matrix==1)[1]
        x_noconst = np.where(matrix==1)[0]
        x = sm.add_constant(x_noconst)
        model = sm.OLS(y,x)
        results = model.fit()
        b, m = results.params
        angle = np.abs(np.degrees(np.arctan(m))) # convert slope to angle in degrees
        angle_list.append(angle) # keep track of angles
        if angle > thresh: # more than thresh degrees slanted
            plot_slanted_image(matrix,i,b,m,plot_dir=f'plots/Image Processing/Slanted Images')
    
    # make into a dataframe
    angle_df = pd.DataFrame(angle_list,columns=['Angle'])
    angle_df.index.name = 'ImageID'
    
    # kde and rug plot of slanted images
    slanted_images_summary_plot(angle_df, thresh, plot_dir=f'plots/Image Processing')

    # images with angle > thresh
    slanted_imageIDs = angle_df[angle_df['Angle']>thresh].index.to_list()

    # determine max width to pad all images
    plot_image_widths(matrixList, matrix_rescaled_list, plot_dir=f'plots/Image Processing')

    # quality control -- which images are too wide (most likely due to incorrect cropping)
    # make sure images actually rescaled to same height
    for idx,matrix in enumerate(matrix_rescaled_list):
        if matrix.shape[0]!=maxHeight:
            print('Incorrect height scaling: ',idx,matrix.shape[0])
    
    # find abnormally wide images
    abnormal_imageIDs = []
    for idx,matrix in enumerate(matrix_rescaled_list):
        width_thresh = 203 ### TODO make this part of GUI
        if matrix.shape[1] > width_thresh: # largest correctly scaled/cropped image is 203
            abnormal_imageIDs.append(idx)
            print('Image too wide: ', idx,matrix.shape[1])
            plot_image(matrix,idx, 'brightfield', plot_dir=f'plots/Image Processing/Wide Images')

    # images to ignore -- slanted or too wide
    imagesIDs2ignore = slanted_imageIDs + abnormal_imageIDs
    
    # save bad image IDs
    badIDs_file = open(f'misc/imagesIDs2ignore-{os.getcwd().split(dirSep)[-1]}.pkl', 'wb') 
    pickle.dump(imagesIDs2ignore,badIDs_file)
    badIDs_file.close()
    np.savetxt(f'misc/imagesIDs2ignore-{os.getcwd().split(dirSep)[-1]}.txt',imagesIDs2ignore,fmt='%d',delimiter=',')
    
    # get max width across all scaled images
    print('Padding images to same width')
    maxWidth = max([x.shape[1] for i,x in enumerate(matrix_rescaled_list) if i not in imagesIDs2ignore])
    
    print(f'Max Width: {maxWidth}; Max Height: {maxHeight}')
    # create new matrix_rescaled_list correcting for slanted/wide images
    # crop slanted/abnormal images that are greater than maxWidth
    # add matrix of np.nan if "bad" matrix (slanted/error)
    matrix_rescaled_list = [x[:,:maxWidth,:] if i not in imagesIDs2ignore else np.full([maxHeight,maxWidth,3], np.nan) for i,x in enumerate(matrix_rescaled_list)]

    # perform padding of each image and merge all together
    bigMatrix = pad_images(matrix_rescaled_list,maxHeight,maxWidth)
    np.save(f'outputData/bigMatrix-{os.getcwd().split(dirSep)[-1]}.npy',bigMatrix)
    print('All Images Processed, Merged, and Saved (bigMatrix.npy).')

    # generate average mouse across all timepoints
    # plot average image
    dataTypeDict = {'radiance':0,'mousePixel':1,'brightfield':2}
    plt.figure() # make new figure
    avgRadianceMatrix = np.nanmean(bigMatrix[:,:,dataTypeDict['radiance'],:],axis=2) # average radiance matrix
    vmin = min(labelDf_all.vmin.values) # get vmin
    vmax = max(labelDf_all.vmax.values) # and vmax
    background = np.nanmean(bigMatrix[:,:,dataTypeDict['brightfield'],:],axis=2) # use brightfield as backgroud of plot
    plt.imshow(background,cmap='Greys_r') # plot brightfield as background first
    mouseMask = np.nanmean(bigMatrix[:,:,dataTypeDict['mousePixel'],:],axis=2)>0 # true/false for each pixel - true if on mouse (>0 means have tumor at that pixel for at least one mouse)
    background[mouseMask] = avgRadianceMatrix[mouseMask] # replace pixels on mouse with radiance values              
    background[~mouseMask] = -999 # make background pixels not on mouse black (ignored by colormap)
    plt.imshow(background,cmap='turbo') # ,norm=matplotlib.colors.LogNorm(vmin,vmax) # normalize color only for radiance
    plt.savefig(f'plots/Image Processing/avg_merged_image-{os.getcwd().split(dirSep)[-1]}.pdf',format='pdf',bbox_inches='tight')
    plt.axis('off')
    plt.savefig(f'plots/Image Processing/avg_merged_image-{os.getcwd().split(dirSep)[-1]}.png',format='png',bbox_inches='tight',pad_inches=0) # need png to display in window
    print('Average image saved.')

    return labelDf_all.set_index(['vmin','vmax'],append=True), maxWidth, maxHeight

def calculate_radiance_from_merged_images(matrix,labelDf,imagesIDs2ignore,image_dir):
  '''
  Function to calculate the radiance from the rescalled/merged images.
  '''

  img_list = list(labelDf.ImageID.values) # imageIDs
  img_list = [idx for idx in img_list if idx not in imagesIDs2ignore] # remove bad images

  # create dataframe with average value on each day for selected region and selected mice
  avg_vals = []
  tot_vals = []
  for img in tqdm(img_list): # loop through each image
    # extract image from big matrix
    img_matrices = matrix[:,:,:,img]
    img_radiance = img_matrices[:,:,0]
    img_mousePixel = img_matrices[:,:,1]
    # img_brightfield = img_matrices[:,:,2] # not used here
    
    # only calculate radiance for pixels that are on the mouse as determined from the mousePixel info
    zeros = np.zeros(img_radiance.shape) # matrix of zeros -- will add radiance values on mouse ontop of this
    mouseMask = img_mousePixel == 1 # true/false for each pixel - true if on mouse
    zeros[mouseMask] = img_radiance[mouseMask] # replace pixels on mouse with radiance values

    # save the region/image where calculating radiance
    plt.figure()
    plt.imshow(zeros,cmap='turbo') # ,norm=matplotlib.colors.LogNorm(vmin,vmax) # normalize color only for radiance
    plt.axis('off')
    plt.savefig(f'{image_dir}/{img}_ROI.pdf')
    
    # calculate total and average radiance of image (ignore -999 which is from padding)
    tot_vals.append(np.nansum([val for val in zeros.flatten() if val != -999])) # total vals in region
    avg_vals.append(np.nanmean([val for val in zeros.flatten() if val != -999])) # average vals in region

  # put values into a dataframe
  avgValsDf = pd.DataFrame(avg_vals,index=img_list,columns=[f'avg_radiance']).rename_axis('ImageID')
  totValsDf = pd.DataFrame(tot_vals,index=img_list,columns=[f'tot_radiance']).rename_axis('ImageID')

  # add metadata information
  print('Adding metadata')
  mice = list(labelDf.reset_index().MouseID.unique()) # list of mice where have images
  dfList = []
  for mouse in tqdm(mice):
    # filter df to have radiance for one mouse at a time
    images = list(labelDf.query('MouseID == @mouse').reset_index().ImageID.unique()) # imageIDs for mouse
    avg = avgValsDf.query('ImageID in @images')
    tot = totValsDf.query('ImageID in @images')
    
    # create new dataframe with info on mice
    df = avg.copy().drop(['avg_radiance'],axis=1)
    df['MouseID']=mouse
    df['Average Radiance']=avg.values
    df['Total Radiance']=tot.values
    df['Date']=labelDf.query('MouseID == @mouse').reset_index().Date.unique()[0]
    df['ExperimentName']=labelDf.query('MouseID == @mouse').reset_index().ExperimentName.unique()[0]
    df['Researcher']=labelDf.query('MouseID == @mouse').reset_index().Researcher.unique()[0]
    df['CAR_Binding']=labelDf.query('MouseID == @mouse').reset_index().CAR_Binding.unique()[0]
    df['CAR_Costimulatory']=labelDf.query('MouseID == @mouse').reset_index().CAR_Costimulatory.unique()[0]
    df['Tumor']=labelDf.query('MouseID == @mouse').reset_index().Tumor.unique()[0] 
    df['TumorCellNumber']=labelDf.query('MouseID == @mouse').reset_index().TumorCellNumber.unique()[0]
    df['TCellNumber']=labelDf.query('MouseID == @mouse').reset_index().TCellNumber.unique()[0]
    df['bloodDonorID']=labelDf.query('MouseID == @mouse').reset_index().bloodDonorID.unique()[0]
    df['Perturbation']=labelDf.query('MouseID == @mouse').reset_index().Perturbation.unique()[0]
    df['Group']=labelDf.query('MouseID == @mouse').reset_index().Group.unique()[0]
    df['Sample']=labelDf.query('MouseID == @mouse').reset_index().Sample.unique()[0]
    df['Time'] = [labelDf.query('ImageID == @imgID').reset_index().Time[0] for imgID in list(labelDf.query('MouseID == @mouse and ImageID not in @imagesIDs2ignore').ImageID.values)]
    df['Day'] = [f'D{x}' for x in list(df.reset_index().Time)]

    # sort df by time
    df = df.sort_values(by=['Time'])

    dfList.append(df)

  df_from_images = pd.concat(dfList).reset_index().set_index(['Date','ExperimentName','Researcher','CAR_Binding','CAR_Costimulatory','Tumor','TumorCellNumber','TCellNumber','bloodDonorID','Perturbation','Group','Day','Time','Sample','MouseID'])

  # replace zero values and those below minimum detection per pixel of 100
  df_from_images = replace_background(df_from_images) # fix background values

  return df_from_images


def calculate_radiance(left,right,top,bottom,text):
    '''
    Function to calculate the radiance from the rescalled/merged images.
    Inputs:
        left, right, top, bottom -- coordinates of rectangle to calculate radiance
        text -- string for selected region
    '''
    print(f'Calculating Radiance ({text}): left={left}, top={top}, right={right}, bottom={bottom}.')
    # reload in the data
    matrix = np.load(f'outputData/bigMatrix-{os.getcwd().split(dirSep)[-1]}.npy') # reload the raw image data
    labelDf_all = pd.read_hdf(f'outputData/labelDf_all-{os.getcwd().split(dirSep)[-1]}.hdf') # reload data that now has metadata for each image
    labelDf = labelDf_all.drop(['Average Pixel Intensity','Average Radiance','Total Radiance','Tumor Fraction'],axis=1).reset_index(['ImageID']) # only want the metadata
    imagesIDs2ignore = loadPickle(f'misc/imagesIDs2ignore-{os.getcwd().split(dirSep)[-1]}.pkl')

    # crop matrix depending on input parameter region
    matrixRegion = matrix[top:bottom,left:right,:,:]

    # calculate radiance for each image
    image_dir = f'plots/Image Processing/ROI Radiance Calculation/left{left}_top{top}_right{right}_bottom{bottom}_{text}'
    if not os.path.exists(image_dir): os.makedirs(image_dir) # make dir to save figures if it doesn't already exist
    df_from_images = calculate_radiance_from_merged_images(matrixRegion,labelDf,imagesIDs2ignore,image_dir)

    data_dir = 'outputData/ROI Radiance Calculation'
    if not os.path.exists(f'{data_dir}/left{left}_top{top}_right{right}_bottom{bottom}_{text}'): os.makedirs(f'{data_dir}/left{left}_top{top}_right{right}_bottom{bottom}_{text}') # make dir to save merged radiance data if it doesn't already exist
    df_from_images.to_pickle(f'{data_dir}/left{left}_top{top}_right{right}_bottom{bottom}_{text}/{os.getcwd().split(dirSep)[-1]}_df_from_images_left{left}_top{top}_right{right}_bottom{bottom}_{text}.pkl')
    print(f'Dataframe with calculated radiance ({text}: left={left}, top={top}, right={right}, bottom={bottom}) saved.')