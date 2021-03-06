#Based off of http://wiki.wxpython.org/GLCanvas
#Lots of help from http://wiki.wxpython.org/Getting%20Started
from OpenGL.GL import *
import wx
from wx import glcanvas

from Primitives3D import *
from PolyMesh import *
from Geodesics import *
from PointCloud import *
from Cameras3D import *
from sys import exit, argv
import random
import numpy as np
import scipy.io as sio
from pylab import cm
import os
import math
import time

DEFAULT_SIZE = wx.Size(1200, 800)
DEFAULT_POS = wx.Point(10, 10)

def saveImageGL(mvcanvas, filename):
	view = glGetIntegerv(GL_VIEWPORT)
	img = wx.EmptyImage(view[2], view[3] )
	pixels = glReadPixels(0, 0, view[2], view[3], GL_RGB,
		             GL_UNSIGNED_BYTE)
	img.SetData( pixels )
	img = img.Mirror(False)
	img.SaveFile(filename, wx.BITMAP_TYPE_PNG)

def saveImage(canvas, filename):
	s = wx.ScreenDC()
	w, h = canvas.size.Get()
	b = wx.EmptyBitmap(w, h)
	m = wx.MemoryDCFromDC(s)
	m.SelectObject(b)
	m.Blit(0, 0, w, h, s, 70, 0)
	m.SelectObject(wx.NullBitmap)
	b.SaveFile(filename, wx.BITMAP_TYPE_PNG)
	

class FaceViewerCanvas(glcanvas.GLCanvas):
	def __init__(self, parent, takeScreenshots, screenshotsPrefix = "", rotationAngle = 0):
		attribs = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24)
		glcanvas.GLCanvas.__init__(self, parent, -1, attribList = attribs)	
		self.context = glcanvas.GLContext(self)
		
		self.parent = parent
		self.takeScreenshots = takeScreenshots
		print "Taking screenshots: %s"%self.takeScreenshots
		self.screenshotCounter = 1
		self.screenshotsPrefix = screenshotsPrefix
		self.rotationAngle = rotationAngle
		#Camera state variables
		self.size = self.GetClientSize()
		#self.camera = MouseSphericalCamera(self.size.x, self.size.y)
		self.camera = MousePolarCamera(self.size.width, self.size.height)
		
		#Main state variables
		self.MousePos = [0, 0]
		self.initiallyResized = False

		self.bbox = BBox3D()
		self.unionbbox = BBox3D()
		random.seed()
		
		#Face mesh variables and manipulation variables
		self.faceMesh = None
		self.displayMeshFaces = True
		self.displayMeshEdges = False
		self.displayMeshVertices = False
		self.displayMeshNormals = False
		self.vertexColors = np.zeros(0)
		
		self.cutPlane = None
		self.displayCutPlane = False
		
		self.GLinitialized = False
		#GL-related events
		wx.EVT_ERASE_BACKGROUND(self, self.processEraseBackgroundEvent)
		wx.EVT_SIZE(self, self.processSizeEvent)
		wx.EVT_PAINT(self, self.processPaintEvent)
		#Mouse Events
		wx.EVT_LEFT_DOWN(self, self.MouseDown)
		wx.EVT_LEFT_UP(self, self.MouseUp)
		wx.EVT_RIGHT_DOWN(self, self.MouseDown)
		wx.EVT_RIGHT_UP(self, self.MouseUp)
		wx.EVT_MIDDLE_DOWN(self, self.MouseDown)
		wx.EVT_MIDDLE_UP(self, self.MouseUp)
		wx.EVT_MOTION(self, self.MouseMotion)		
		#self.initGL()
	
	def initPointCloud(self, pointCloud):
		self.pointCloud = pointCloud
	
	def viewFromFront(self, evt):
		self.camera.centerOnBBox(self.bbox, theta = -math.pi/2, phi = math.pi/2)
		self.Refresh()
	
	def viewFromTop(self, evt):
		self.camera.centerOnBBox(self.bbox, theta = -math.pi/2, phi = 0)
		self.Refresh()
	
	def viewFromSide(self, evt):
		self.camera.centerOnBBox(self.bbox, theta = -math.pi, phi = math.pi/2)
		self.Refresh()
	
	def displayMeshFacesCheckbox(self, evt):
		self.displayMeshFaces = evt.Checked()
		self.Refresh()

	def displayMeshEdgesCheckbox(self, evt):
		self.displayMeshEdges = evt.Checked()
		self.Refresh()
		
	def displayCutPlaneCheckbox(self, evt):
		self.displayCutPlane = evt.Checked()
		self.Refresh()

	def displayMeshVerticesCheckbox(self, evt):
		self.displayMeshVertices = evt.Checked()
		self.Refresh()
	
	def CutWithPlane(self, evt):
		if self.cutPlane:
			self.faceMesh.sliceBelowPlane(self.cutPlane, False)
			self.faceMesh.starTriangulate() #TODO: This is a patch to deal with "non-planar faces" added
			self.Refresh()
	
	def ComputeGeodesicDistances(self, evt):
		if not self.faceMesh:
			print "ERROR: Haven't loaded mesh yet"
			return
		D = getGeodesicDistancesFMM(self.faceMesh)
		D = D[0, :]
		minD = min(D)
		maxD = max(D)
		print "Finished computing geodesic distances"
		print "minD = %g, maxD = %g"%(minD, maxD)
		N = D.shape[0]
		cmConvert = cm.get_cmap('jet')
		self.vertexColors = np.zeros((N, 3))
		for i in range(0, N):
			self.vertexColors[i, :] = cmConvert((D[i] - minD)/(maxD - minD))[0:3]
		self.Refresh()
	
	def processEraseBackgroundEvent(self, event): pass #avoid flashing on MSW.

	def processSizeEvent(self, event):
		self.size = self.GetClientSize()
		self.SetCurrent(self.context)
		glViewport(0, 0, self.size.width, self.size.height)
		if not self.initiallyResized:
			#The canvas gets resized once on initialization so the camera needs
			#to be updated accordingly at that point
			self.camera = MousePolarCamera(self.size.width, self.size.height)
			self.camera.centerOnBBox(self.bbox, math.pi/2, math.pi/2)
			self.initiallyResized = True

	def processPaintEvent(self, event):
		dc = wx.PaintDC(self)
		self.SetCurrent(self.context)
		if not self.GLinitialized:
			self.initGL()
			self.GLinitialized = True
		self.repaint()

	def repaint(self):
		#Set up projection matrix
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		farDist = (self.camera.eye - self.bbox.getCenter()).Length()*2
		#This is to make sure we can see on the inside
		farDist = max(farDist, self.unionbbox.getDiagLength()*2)
		nearDist = farDist/50.0
		gluPerspective(180.0*self.camera.yfov/M_PI, float(self.size.x)/self.size.y, nearDist, farDist)
		
		#Set up modelview matrix
		self.camera.gotoCameraFrame()	
		glClearColor(0.0, 0.0, 0.0, 0.0)
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		glLightfv(GL_LIGHT0, GL_POSITION, [3.0, 4.0, 5.0, 0.0]);
		glLightfv(GL_LIGHT1, GL_POSITION,  [-3.0, -2.0, -3.0, 0.0]);
		
		glEnable(GL_LIGHTING)
		glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [0.8, 0.8, 0.8, 1.0]);
		glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])
		glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, 64)
		
		if self.faceMesh:
			self.faceMesh.renderGL(self.displayMeshEdges, self.displayMeshVertices, self.displayMeshNormals, self.displayMeshFaces, None)
		
		if self.displayCutPlane:
			t = farDist*self.camera.towards
			r = t % self.camera.up
			u = farDist*self.camera.up
			dP0 = farDist / 10.0
			#dP0 = 1
			P0 = self.camera.eye - (dP0/farDist/10.0)*r
			cutPlaneMesh = getRectMesh(P0 + t + u, P0 + t - u, P0 - t - u, P0 - t + u)
			glDisable(GL_LIGHTING)
			glColor3f(0, 1, 0)
			cutPlaneMesh.renderGL()
			self.cutPlane = Plane3D(P0, r)
		
		self.SwapBuffers()
	
	def initGL(self):		
		glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
		glLightModeli(GL_LIGHT_MODEL_LOCAL_VIEWER, GL_TRUE)
		glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
		glEnable(GL_LIGHT0)
		glLightfv(GL_LIGHT1, GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
		glEnable(GL_LIGHT1)
		glEnable(GL_NORMALIZE)
		glEnable(GL_LIGHTING)
		glEnable(GL_DEPTH_TEST)

	def handleMouseStuff(self, x, y):
		#Invert y from what the window manager says
		y = self.size.height - y
		self.MousePos = [x, y]

	def MouseDown(self, evt):
		x, y = evt.GetPosition()
		self.CaptureMouse()
		self.handleMouseStuff(x, y)
		self.Refresh()
	
	def MouseUp(self, evt):
		x, y = evt.GetPosition()
		self.handleMouseStuff(x, y)
		self.ReleaseMouse()
		self.Refresh()

	def MouseMotion(self, evt):
		x, y = evt.GetPosition()
		[lastX, lastY] = self.MousePos
		self.handleMouseStuff(x, y)
		dX = self.MousePos[0] - lastX
		dY = self.MousePos[1] - lastY
		if evt.Dragging():
			if evt.MiddleIsDown():
				self.camera.translate(dX, dY)
			elif evt.RightIsDown():
				self.camera.zoom(-dY)#Want to zoom in as the mouse goes up
			elif evt.LeftIsDown():
				self.camera.orbitLeftRight(dX)
				self.camera.orbitUpDown(dY)
		self.Refresh()

class FaceViewerFrame(wx.Frame):
	(ID_LOADDATASET, ID_SAVEDATASET) = (0, 1)
	
	def __init__(self, parent, id, title, pos=DEFAULT_POS, size=DEFAULT_SIZE, style=wx.DEFAULT_FRAME_STYLE, name = 'GLWindow', takeScreenshots = False, screenshotsPrefix = "", rotationAngle = 0):
		style = style | wx.NO_FULL_REPAINT_ON_RESIZE
		super(FaceViewerFrame, self).__init__(parent, id, title, pos, size, style, name)
		#Initialize the menu
		self.CreateStatusBar()
		
		self.size = size
		self.pos = pos
		print "FaceViewerFrameSize = %s, pos = %s"%(self.size, self.pos)
		
		filemenu = wx.Menu()
		menuOpenFace = filemenu.Append(FaceViewerFrame.ID_LOADDATASET, "&Load Face","Load a triangular mesh representing a face")
		self.Bind(wx.EVT_MENU, self.OnLoadFace, menuOpenFace)
		menuSaveFace = filemenu.Append(FaceViewerFrame.ID_SAVEDATASET, "&Save Face", "Save the edited triangular mesh")
		self.Bind(wx.EVT_MENU, self.OnSaveFace, menuSaveFace)
		menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		
		# Creating the menubar.
		menuBar = wx.MenuBar()
		menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
		self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
		self.glcanvas = FaceViewerCanvas(self, takeScreenshots, screenshotsPrefix, rotationAngle)
		
		self.rightPanel = wx.BoxSizer(wx.VERTICAL)
		
		#Buttons to go to a default view
		viewPanel = wx.BoxSizer(wx.HORIZONTAL)
		topViewButton = wx.Button(self, -1, "Top")
		self.Bind(wx.EVT_BUTTON, self.glcanvas.viewFromTop, topViewButton)
		viewPanel.Add(topViewButton, 0, wx.EXPAND)
		sideViewButton = wx.Button(self, -1, "Side")
		self.Bind(wx.EVT_BUTTON, self.glcanvas.viewFromSide, sideViewButton)
		viewPanel.Add(sideViewButton, 0, wx.EXPAND)
		frontViewButton = wx.Button(self, -1, "Front")
		self.Bind(wx.EVT_BUTTON, self.glcanvas.viewFromFront, frontViewButton)
		viewPanel.Add(frontViewButton, 0, wx.EXPAND)
		self.rightPanel.Add(wx.StaticText(self, label="Views"), 0, wx.EXPAND)
		self.rightPanel.Add(viewPanel, 0, wx.EXPAND)
		
		#Checkboxes for displaying data
		self.displayMeshFacesCheckbox = wx.CheckBox(self, label = "Display Mesh Faces")
		self.displayMeshFacesCheckbox.SetValue(True)
		self.Bind(wx.EVT_CHECKBOX, self.glcanvas.displayMeshFacesCheckbox, self.displayMeshFacesCheckbox)
		self.rightPanel.Add(self.displayMeshFacesCheckbox, 0, wx.EXPAND)
		self.displayMeshEdgesCheckbox = wx.CheckBox(self, label = "Display Mesh Edges")
		self.displayMeshEdgesCheckbox.SetValue(False)
		self.Bind(wx.EVT_CHECKBOX, self.glcanvas.displayMeshEdgesCheckbox, self.displayMeshEdgesCheckbox)
		self.rightPanel.Add(self.displayMeshEdgesCheckbox, 0, wx.EXPAND)
		self.displayMeshVerticesCheckbox = wx.CheckBox(self, label = "Display Mesh Points")
		self.displayMeshVerticesCheckbox.SetValue(False)
		self.Bind(wx.EVT_CHECKBOX, self.glcanvas.displayMeshVerticesCheckbox, self.displayMeshVerticesCheckbox)
		self.rightPanel.Add(self.displayMeshVerticesCheckbox, 0, wx.EXPAND)

		#Checkboxes and buttons for manipulating the cut plane
		self.rightPanel.Add(wx.StaticText(self, label="Cutting Plane"), 0, wx.EXPAND)
		self.displayCutPlaneCheckbox = wx.CheckBox(self, label = "Display Cut Plane")
		self.displayCutPlaneCheckbox.SetValue(False)
		self.Bind(wx.EVT_CHECKBOX, self.glcanvas.displayCutPlaneCheckbox, self.displayCutPlaneCheckbox)
		self.rightPanel.Add(self.displayCutPlaneCheckbox, 0, wx.EXPAND)
		CutWithPlaneButton = wx.Button(self, -1, "Cut With Plane")
		self.Bind(wx.EVT_BUTTON, self.glcanvas.CutWithPlane, CutWithPlaneButton)
		self.rightPanel.Add(CutWithPlaneButton)
		
		#Buttons for computing geodesic distance
		self.rightPanel.Add(wx.StaticText(self, label="Geodesic Distances"), 0, wx.EXPAND)
		ComputeGeodesicButton = wx.Button(self, -1, "Compute Geodesic Distances")
		self.Bind(wx.EVT_BUTTON, self.glcanvas.ComputeGeodesicDistances, ComputeGeodesicButton)
		self.rightPanel.Add(ComputeGeodesicButton)

		#Finally add the two main panels to the sizer		
		self.sizer = wx.BoxSizer(wx.HORIZONTAL)
		#cubecanvas = CubeCanvas(self)
		#self.sizer.Add(cubecanvas, 2, wx.EXPAND)
		self.sizer.Add(self.glcanvas, 2, wx.EXPAND)
		self.sizer.Add(self.rightPanel, 0, wx.EXPAND)
		
		self.SetSizer(self.sizer)
		self.Layout()
		#self.SetAutoLayout(1)
		#self.sizer.Fit(self)
		self.Show()
	
	def OnLoadFace(self, evt):
		dlg = wx.FileDialog(self, "Choose a file", ".", "", "OBJ files (*.obj)|*.obj|OFF files (*.off)|*.off", wx.OPEN)
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetFilename()
			dirname = dlg.GetDirectory()
			filepath = os.path.join(dirname, filename)
			print dirname
			self.glcanvas.faceMesh = PolyMesh()
			print "Loading face %s..."%filename
			self.glcanvas.faceMesh.loadFile(filepath)
			print "Finished loading face\n %s"%self.glcanvas.faceMesh
			#print "Deleting all but largest connected component..."
			#self.glcanvas.faceMesh.deleteAllButLargestConnectedComponent()
			print self.glcanvas.faceMesh
			self.glcanvas.bbox = self.glcanvas.faceMesh.getBBox()
			print "Face BBox: %s\n"%self.glcanvas.bbox
			self.glcanvas.camera.centerOnBBox(self.glcanvas.bbox, theta = -math.pi/2, phi = math.pi/2)
			self.glcanvas.Refresh()
		dlg.Destroy()
		return

	def OnSaveFace(self, evt):
		dlg = wx.FileDialog(self, "Choose a file", ".", "", "*", wx.SAVE)
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetFilename()
			dirname = dlg.GetDirectory()
			filepath = os.path.join(dirname, filename)
			self.glcanvas.faceMesh.saveFile(filepath, True)
			self.glcanvas.Refresh()
		dlg.Destroy()
		return

	def OnExit(self, evt):
		self.Close(True)
		return

class FaceViewer(object):
	def __init__(self, filename = None, ts = False, sp = "", ra = 0):
		app = wx.App()
		frame = FaceViewerFrame(None, -1, 'FaceViewer', takeScreenshots = ts, screenshotsPrefix = sp, rotationAngle = ra)
		if (filename):
			frame.OnLoadAzElZDataset(filename)
		frame.Show(True)
		app.MainLoop()
		app.Destroy()

if __name__ == '__main__':
	filename = None
	if len(argv) > 1:
		filename = argv[1]
	takeScreenshots = False
	screenshotsPrefix = ""
	rotationAngle = 0
	if len(argv) >= 3:
		takeScreenshots = True
		screenshotsPrefix = argv[2]
	if len(argv) >= 4:
		rotationAngle = int(argv[3])
	viewer = FaceViewer(filename, takeScreenshots, screenshotsPrefix, rotationAngle)
