from pydarn.proc.pygridIo import *
from utils.timeUtils import *
from utils.geoPack import *
	
def mergePygrid(dateStr,hemi='north',times=[0,2400],interval=120,vb=0):
	"""
	*******************************
	PACKAGE: pydarn.proc.pygridLib
	FUNCTION: makePyrid(dateStr,rad,[times],[fileType],[interval],[vb],[filter],[plot]):
	
	reads in fitted radar data and puts it into a geospatial grid
	
	INPUTS:
		dateStr : a string containing the target date in yyyymmdd format
		rad: the 3 letter radar code, e.g. 'bks'
		[times]: the range of times for which the file should be read in
			MINIMIZED hhmm format, ie [23,456], NOT [0023,0456]
			default = [0,2400]
		[interval]: the time interval at which to do the merging
			in seconds; default = 120
	OUTPUTS:
		NONE
		
	Written by AJ 20120807
	*******************************
	"""
	import datetime,pydarn,os,string,math
	
	#convert date string, start time, end time to datetime
	myDate = yyyymmddToDate(dateStr)
	hr1,hr2 = int(math.floor(times[0]/100.)),int(math.floor(times[1]/100.))
	min1,min2 = int(times[0]-hr1*100),int(times[1]-hr2*100)
	stime = myDate.replace(hour=hr1,minute=min1)
	if(hr2 == 24):
		etime = myDate+datetime.timedelta(days=1)
	else:
		etime = myDate.replace(hour=hr2,minute=min2)
		
	baseDir = os.environ['DATADIR']+'/pygrid'
	network = pydarn.radar.network();
	codes = network.getAllCodes();
	myFiles,fileNames = [],[]
	for c in codes:
		glat = network.getRadarByCode(c).getSiteByDate(stime).geolat
		if(hemi == 'north' and glat < 0): continue
		if(hemi == 'south' and glat >= 0): continue
		
		radDir = baseDir+'/'+c
		if not os.path.exists(radDir):
			print 'dir '+radDir+' does not exist'
			continue
		
		fileName = radDir+'/'+dateStr+'.'+c+'.pygrid.hdf5.bz2'
		if not os.path.exists(fileName):
			fileName = string.replace(fileName,'.bz2','')
			if not os.path.exists(fileName):
				print 'file '+fileName+'[.bz2] does not exist'
				continue
		else:
			print 'bunzip2 '+fileName
			os.system('bunzip2 '+fileName)
			fileName = string.replace(fileName,'.bz2','')
		
		print 'opening: '+fileName
		fileNames.append(fileName)
		myFiles.append(openPygrid(fileName,'r'))
		
	
	if(myFiles == []): return
	
	d = baseDir+'/'+hemi
	if not os.path.exists(d):
		os.makedirs(d)
	outName = d+'/'+dateStr+'.'+hemi+'.pygrid.hdf5'
	outFile = openPygrid(outName,'w')
	
	g = pygrid()
	ctime = stime
	#until we reach the designated end time
	while ctime < etime:
		#boundary time
		bndT = ctime+datetime.timedelta(seconds=interval)
		#remove vectors from the grid object
		g.delVecs()
		#verbose option
		if(vb==1): print ctime

		
		for f in myFiles:
			readPygridRec(f,g,datetimeToEpoch(ctime),\
			datetimeToEpoch(bndT))
			
		if(g.nVecs > 0):
			g.stime = ctime
			g.etime = bndT
			g.mergeVecs()
			writePygridRec(outFile,g)
		
		#reassign the current time we are at
		ctime = bndT
	
	#close the files
	closePygrid(outFile)
	for f in myFiles: closePygrid(f)
	
	for f in fileNames:
		print 'zipping: '+f
		os.system('bzip2 '+f)
		

def makePygrid(dateStr,rad,times=[0,2400],fileType='fitex',interval=120,vb=0,filter=1):
	
	"""
	*******************************
	PACKAGE: pydarn.proc.prgridLib
	FUNCTION: makePygrid(dateStr,rad,[times],[fileType],[interval],[vb],[filter],[plot]):
	
	reads in fitted radar data and puts it into a geospatial grid
	
	INPUTS:
		dateStr : a string containing the target date in yyyymmdd format
		rad: the 3 letter radar code, e.g. 'bks'
		[times]: the range of times for which the file should be read in
			MINIMIZED hhmm format, ie [23,456], NOT [0023,0456]
			default = [0,2400]
		[fileType]: 'fitex', 'fitacf', or 'lmfit'; default = 'fitex'
		[interval]: the time interval at which to do the gridding
			in seconds; default = 120
		[filter]: 1 to boxcar filter, 0 for normal data; default = 1
	OUTPUTS:
		NONE
		
	Written by AJ 20120807
	*******************************
	"""
	import pydarn,math,datetime,aacgm,os

	
	#convert date string, start time, end time to datetime
	myDate = yyyymmddToDate(dateStr)
	hr1,hr2 = int(math.floor(times[0]/100.)),int(math.floor(times[1]/100.))
	min1,min2 = int(times[0]-hr1*100),int(times[1]-hr2*100)
	stime = myDate.replace(hour=hr1,minute=min1)
	if(hr2 == 24):
		etime = myDate+datetime.timedelta(days=1)
	else:
		etime = myDate.replace(hour=hr2,minute=min2)
	
	#read the radar data
	myData = pydarn.io.radDataRead(dateStr,rad,time=times,filter=filter)
	#check for data in this time period
	assert(myData.nrecs > 0),'error, no data for this time period'
	#get a radar site object
	site = pydarn.radar.network().getRadarByCode(rad).getSiteByDate(myData.times[0])
	myFov = pydarn.radar.radFov.fov(site=site,rsep=myData[myData.times[0]]['prm']['rsep'],\
	ngates=site.maxgate+1,nbeams=site.maxbeam+1)
	
	#create a 2D list to hold coords of RB cells
	coordsList = [[None]*site.maxgate for _ in range(site.maxbeam)]
	for i in range(site.maxbeam):
		for j in range(site.maxgate):
			t=myData.times[0]
			arr1=aacgm.aacgmConv(myFov.latCenter[i][j],myFov.lonCenter[i][j],300,0)
			arr2=aacgm.aacgmConv(myFov.latCenter[i][j+1],myFov.lonCenter[i][j+1],300,0)
			azm = greatCircleAzm(arr1[0],arr1[1],arr2[0],arr2[1])
			coordsList[i][j] = [arr1[0],arr1[1],azm]

	#a list for all the grid objects
	myGrids = []
	#create a pygrid object
	g = pygrid()
	#initialize start time
	ctime = stime
	lastInd = 0


	d = os.environ['DATADIR']+'/pygrid/'+rad
	if not os.path.exists(d):
		os.makedirs(d)
	fileName = d+'/'+dateStr+'.'+rad+'.pygrid.hdf5'
	#open a pygrid file
	gFile = openPygrid(fileName,'w')
	
	#until we reach the designated end time
	while ctime < etime:
		#boundary time
		bndT = ctime+datetime.timedelta(seconds=interval)
		#remove vectors from the grid object
		g.delVecs()
		#verbose option
		if(vb==1): print ctime
		#iterate through the radar data
		for i in range(lastInd,myData.nrecs):
			#current time of radar data
			t = myData.times[i]
			#are we in the target time interval?
			if(ctime < t <= bndT): 
				#enter the radar data into the grid
				g.enterData(myData[t],coordsList)
			#if we have exceeded the boundary time
			elif(t >= bndT): break
		#record the last record we examined
		lastInd = i
		#if we have > 0 gridded vector
		if(g.nVecs > 0):
			#record some information
			g.stime = ctime
			g.etime = bndT
			#average is LOS vectors
			g.averageVecs()
			#write to the hdf5 file
			writePygridRec(gFile,g)
			
		#reassign the current time we are at
		ctime = bndT
		
		
	closePygrid(gFile)
	if(os.path.exists(fileName+'.bz2')): os.system('rm '+fileName+'.bz2')
	os.system('bzip2 '+fileName)
			
	
class pygridVec(object):
	"""
	*******************************
	PACKAGE: pydarn.proc.pygridLib
	CLASS: pygridVec
	
	a class defining a single gridded vector
	
	DECLARATION: 
		myVel = pydarn.proc.pygridLib.pygridVec(v,w_l,p_l,stid,time,bmnum,rng,azm):
	MEMBERS:
		v : Doppler velocity
		w_l : spectral width
		p_l : power
		stid : station id
		time : time of the measurement
		bmnum : beam number of the measurement
		rng : range gate of the measurement
		azm : azimuth of the measurement

	Written by AJ 20120907
	*******************************
	"""
	
	def __init__(self,v,w_l,p_l,stid,time,bmnum,rng,azm):
		
		#initialize all the values, pretty self-explanatory
		self.v = v
		self.w_l = w_l
		self.p_l = p_l
		self.stid = stid
		self.time = time
		self.azm = azm
		self.bmnum = bmnum
		self.rng = rng
		
		
class mergeVec(object):
	"""
	*******************************
	PACKAGE: pydarn.proc.pygridLib
	CLASS: mergeVec
	
	a class defining a single merged vector
	
	DECLARATION: 
		myVel = pydarn.proc.pygridLib.pygridVec(v,w_l,p_l,stid,time,bmnum,rng,azm):
	MEMBERS:
		v : Doppler velocity
		w_l : spectral width
		p_l : power
		stids : station id list
		azm : azimuth of the measurement

	Written by AJ 20120918
	*******************************
	"""
	
	def __init__(self,v,w_l,p_l,stid1,stid2,azm):
		
		#initialize all the values, pretty self-explanatory
		self.v = v
		self.w_l = w_l
		self.p_l = p_l
		self.stids = [stid1,stid2]
		self.rng = rng
		
		
class pygridCell(object):
	"""
	*******************************
	PACKAGE: pydarn.proc.pygridLib
	CLASS: pygridCell
	
	a class defining a single grid cell

	EXAMPLES:
	
	DECLARATION: 
		myCell = pydarn.proc.pygridLib.pygridCell(botLat,topLat,leftLon,rightLon)
	MEMBERS:
		bl : bottom left corner in [lat,mlt]
		tl : bottom left corner in [lat,mlt]
		tr : top right corner in [lat,mlt]
		br : bottom right corner in [lat,mlt]
		center : the center coordinate pair in [lat,mlt]
		nVecs : the number of gridded vectors in this cell
		vecs : a list to hold the pygridVec objects
		
	Written by AJ 20120907
	*******************************
	"""
	
	def __init__(self,lat1,lat2,mlt1,mlt2,n):
		import math
		
		#define the 4 corners of the cell
		self.bl = [lat1,mlt1]
		self.tl = [lat2,mlt1]
		self.tr = [lat2,mlt2]
		self.br = [lat1,mlt2]
		
		self.index = int(math.floor(lat1))*500+n
		
		#check for a wrap around midnight (causes issues with mean) and then
		#calculate the center point of the cell
		if(mlt2 < mlt1): self.center = [(lat1+lat2)/2.,(24.-mlt1+mlt2)/2.]
		else: self.center = [(lat1+lat2)/2.,(mlt1+mlt2)/2.]
		
		#initialize number of grid vectors in this cell and the list to hold them
		self.nVecs = 0
		self.allVecs = []
		self.nAvg = 0
		self.avgVecs = []
		self.mrgVec = []
		
		
class latCell(object):
	"""
	*******************************
	PACKAGE: pydarn.proc.pygridLib
	CLASS: latCell
	
	a class to hold the information for a single latitude
		for a geospatial grid
	
	DECLARATION: 
		myLat = pydarn.proc.pygridLib.latCell()
	MEMBERS:
		nCells : the number of pygridCells contained in this latCell
		botLat : the lower latitude limit of thsi cell
		topLat : the upper latitude limit of this cell
		delLon : the step size (in degrees) in longitude for this
			latCell
		cells : a list of the pygridCell objects
		
	
	Written by AJ 20120907
	*******************************
	"""
	
	def __init__(self,lat):
		import math,aacgm
		#calculate number of pygridCells, defined in Ruohoniemi and Baker
		self.nCells = int(round(360.*math.sin(math.radians(90.-lat))))
		#bottom latitude boundary of this latCell
		self.botLat = lat
		#latitude step size of this cell
		self.delLon = 360./self.nCells
		#top latitude boundary of this cell
		self.topLat = lat+1
		#list for pygridCell objects
		self.cells = []
		
		#iterate over all longitudinal cells
		for i in range(0,self.nCells):
			#calculate left and right mlt boundaries for this pygridCell
			mlt1 = aacgm.mltFromYmdhms(2012,1,1,0,0,0,self.delLon*i)
			mlt2 = aacgm.mltFromYmdhms(2012,1,1,0,0,0,self.delLon*(i+1))

			#create a new pygridCell object and append it to the list
			self.cells.append(pygridCell(self.botLat,self.topLat,mlt1,mlt2,i))
		
		
class pygrid(object):
	"""
	*******************************
	PACKAGE: pydarn.proc.pygridLib
	CLASS: pygrid
	
	the top level class for defining a geospatial grid for 
		velocity gridding

	EXAMPLES:
	
	DECLARATION: 
		myGrid = pydarn.proc.pygridLib.pygrid()
	MEMBERS:
		lats : a list of latCell objects
		nLats : an integer number equal to the number of
			items in the lats list
		delLat : the spacing between latCell objects
		nVecs : the number of gridded vectors in the pygrid object
		
	
	Written by AJ 20120907
	*******************************
	"""
	
	def __init__(self):
		import math 
		
		self.nVecs = 0
		self.nAvg = 0
		self.lats = []
		self.nLats = 90
		
		#latitude step size
		self.delLat = 90./self.nLats
		
		self.stime = None
		self.etime = None
		
		#for all the latitude steps
		for i in range(0,self.nLats):
			#create a new latCell object and append it to the list
			l = latCell(float(i)*self.delLat)
			self.lats.append(l)
			
	def delVecs(self):
		"""
		*******************************
		PACKAGE: pydarn.proc.pygridLib
		FUNCTION: pygrid.delVecs():
		BELONGS TO: CLASS: pydarn.proc.pygridLib.pygrid
		
		delete all vectors from a pygrid object
		
		INPUTS:
			None
		OUTPUTS:
			None
			
		EXAMPLE:
			myGrid.delVecs()
			
		Written by AJ 20120911
		*******************************
		"""
		self.nVecs = 0
		self.nAvg = 0
		
		for l in self.lats:
			for c in l.cells:
				c.allVecs = [];
				c.nVecs = 0;
				c.avgVecs = [];
				c.nAvg = 0
				c.mrgVec = []
			
	def mergeVecs(self):
		"""
		*******************************
		PACKAGE: pydarn.proc.pygridLib
		FUNCTION: pygrid.mergeVecs():
		BELONGS TO: CLASS: pydarn.proc.pygridLib.pygrid
		
		go through all grid cells and average the vectors in 
		cells with more than 1 vector
		
		INPUTS:
			None
		OUTPUTS:
			None
			
		EXAMPLE:
			myGrid.averageVecs()
			
		Written by AJ 20120917
		*******************************
		"""
		
		import numpy as np
		import math
		from numpy import linalg as la
		
		for l in self.lats:
			for c in l.cells:
				if(c.nAvg > 0): print c.nAvg
				if(c.nAvg > 1):
					v1,v2 = c.avgVecs[0],c.avgVecs[1]
					a1,a2 = math.radians(v1.azm),math.radians(v2.azm)
					if(abs(a2-a1) < math.radians(20)): continue
					
					arr = np.array([[math.cos(a1),math.sin(a1)],[math.cos(a2),math.sin(a2)]])
					inv = la.inv(arr)
					
					v_n = inv[0][0]*v1.v+inv[0][1]*v2.v
					v_e = inv[1][0]*v1.v+inv[1][1]*v2.v
					
					vel = math.sqrt(v_n*v_n + v_e*v_e)
					azm = math.degrees(math.atan2(v_e,v_n))
					
					print v1.v,v1.azm
					print v2.v,v2.azm
					print vel,azm
					print ""
					
	def averageVecs(self):
		"""
		*******************************
		PACKAGE: pydarn.proc.pygridLibLib
		FUNCTION: pygrid.averageVecs():
		BELONGS TO: CLASS: pydarn.proc.pygridLibLib.pygrid
		
		go through all grid cells and average the vectors in 
		cells with more than 1 vector
		
		INPUTS:
			None
		OUTPUTS:
			None
			
		EXAMPLE:
			myGrid.averageVecs()
			
		Written by AJ 20120917
		*******************************
		"""
		import numpy
		
		for l in self.lats:
			for c in l.cells:
				if(c.nVecs > 0):
					tmpV = [[]*1 for _ in range(50)]
					tmpA = [[]*1 for _ in range(50)]
					tmpW,tmpP = [],[]
					for v in c.allVecs:
						tmpV[v.bmnum].append(v.v)
						tmpA[v.bmnum].append(v.azm)
						tmpW.append(v.w_l)
						tmpP.append(v.p_l)
					v,a = [],[]
					for i in range(50):
						if(tmpV[i] != []):
							v.append(numpy.mean(numpy.array(tmpV[i])))
							a.append(numpy.mean(numpy.array(tmpA[i])))
					c.avgVecs.append(pygridVec(numpy.mean(numpy.array(v)),numpy.mean(numpy.array(tmpW)),\
					numpy.mean(numpy.array(tmpP)),c.allVecs[0].stid,c.allVecs[0].time,-1,-1,numpy.mean(numpy.array(a))))
					self.nAvg += 1
					c.nAvg += 1

				
	def enterData(self,myData,coordsList):
		"""
		*******************************
		PACKAGE: pydarn.proc.pygridLib
		FUNCTION pygrid.enterData():
		
		inserts radar fitacf data into a pygrid object
		
		BELONGS TO: CLASS: pydarn.proc.pygridLib.pygrid

		INPUTS:
			myData: a pydarn.io.radDataTypes.beam object
			coordsList: a 2D list containing the coords [lat,lon,azm] 
				corresponding to range-beam cells
		OUTPUTS:
			None
			
		EXAMPLE:
			myGrid.enterData(myBeam,myCoords)
			
		Written by AJ 20120911
		*******************************
		"""
		import math,aacgm,time
		
		#go through all scatter points on this beam
		for i in range(0,myData['fit']['npnts']):
			
			#check for good ionospheric scatter
			if(myData['fit']['gflg'][i] == 0 and myData['fit']['v'][i] != 0.0):
				
				#range gate number
				rng = myData['fit']['slist'][i]
				#get coords of r-b cell
				myPos = coordsList[myData['prm']['bmnum']][rng]
				#latitudinal index
				latInd = int(math.floor(myPos[0]/self.delLat))
				
				#convert coords to mlt
				mlt1 = aacgm.mltFromEpoch(time.mktime(myData['prm']['time'].timetuple()),myPos[1])
				
				#compensate for neg. direction is away from radar
				if(myData['fit']['v'][i] > 0.): azm = (myPos[2]+180+360)%360
				else: azm = (myPos[2]+360)%360

				#longitudinal index
				lonInd = int(math.floor(mlt1/24.*360./self.lats[latInd].delLon))
				
				#create a pygridVec object and append it to the list of pygridCells
				self.lats[latInd].cells[lonInd].allVecs.append(pygridVec(abs(myData['fit']['v'][i]),myData['fit']['w_l'][i],\
				myData['fit']['p_l'][i],myData['prm']['stid'],myData['prm']['time'],myData['prm']['bmnum'],rng,azm))
				
				#increment number of vectors in grid cell and pygrid object
				self.lats[latInd].cells[lonInd].nVecs += 1
				self.nVecs += 1
			
			
			