#Based off of http://wiki.wxpython.org/GLCanvas
#Lots of help from http://wiki.wxpython.org/Getting%20Started
from OpenGL.GL import *
import wx
from wx import glcanvas

from Primitives3D import *
from PolyMesh import *
from LaplacianMesh import *
from Geodesics import *
from PointCloud import *
from Cameras3D import *
from ICP import *
from GetFace import *
from sys import exit, argv
import random
import numpy as np
import scipy.io as sio
from pylab import cm
import os
import subprocess
import math
import time
import subprocess

DEFAULT_SIZE = wx.Size(1200, 800)
DEFAULT_POS = wx.Point(10, 10)
PRINCIPAL_AXES_SCALEFACTOR = 1

(STATE_INTRO, STATE_SHOWPOINTS, STATE_SHOWMESH, STATE_SHOWICP, STATE_SHOWSTRETCH, STATE_FINALMATCHING, STATE_DECAY) = (0, 1, 2, 3, 4, 5, 6)

(SHOWPOINTS_ZOOMIN, SHOWPOINTS_ROTATELEFT, SHOWPOINTS_ROTATERIGHT, SHOWPOINTS_ZOOMOUT) = (0, 1, 2, 3)

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
	

class MeshViewerCanvas(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribs = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24)
		glcanvas.GLCanvas.__init__(self, parent, -1, attribList = attribs)	
		self.context = glcanvas.GLContext(self)
		
		self.parent = parent
		#Camera state variables
		self.size = self.GetClientSize()
		#self.camera = MouseSphericalCamera(self.size.x, self.size.y)
		self.camera = MousePolarCamera(self.size.width, self.size.height)
		
		#Main state variables
		self.MousePos = [0, 0]
		self.initiallyResized = False

		random.seed()
		
		#GUI State Variables
		self.GUIState = STATE_INTRO
		self.GUISubstate = -1
		#Head Mesh
		self.headMesh = PolyMesh()
		#self.headMesh.loadFile('NotreDame.off')
		self.rotAngle = 0
		self.zoom = 0
		#User's face
		self.userMesh = None
		
		self.bbox = self.headMesh.getBBox()
		self.camera.centerOnBBox(self.bbox, theta = -math.pi/2, phi = math.pi/2)
		self.zCenter = (self.bbox.zmax + self.bbox.zmin) / 2.0
		
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
		self.initGL()
	
	def startButtonHandler(self, evt):
		print "Starting Face capture..."
		#os.popen3("SingleFace.exe") #Captures the face
		process = subprocess.Popen("SingleFace", shell=True, stdout=subprocess.PIPE)
		process.wait()
		print "FINISHED CAPTURE"
		extractMeshFiles() #Convert the captured data to a triangulated mesh
		self.userMesh = LaplacianMesh()
		self.userMesh.loadFile("out.off")
		self.bbox = self.userMesh.getBBox()
		self.camera.centerOnBBox(self.bbox, theta = -math.pi/2, phi = math.pi/2)
		self.GUIState = STATE_SHOWPOINTS
		self.GUISubstate = SHOWPOINTS_ZOOMIN
		self.zoom = 0
		self.repaint()

	def processEraseBackgroundEvent(self, event): pass #avoid flashing on MSW.

	def processSizeEvent(self, event):
		self.size = self.GetClientSize()
		self.SetCurrent(self.context)
		glViewport(0, 0, self.size.width, self.size.height)
		if not self.initiallyResized:
			#The canvas gets resized once on initialization so the camera needs
			#to be updated accordingly at that point
			self.camera = MousePolarCamera(self.size.width, self.size.height, )
			self.camera.centerOnBBox(self.bbox, theta = -math.pi/2, phi = math.pi/2)
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
		farDist = max(farDist, self.bbox.getDiagLength()*2)
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
		
		self.zCenter = (self.bbox.zmax + self.bbox.zmin) / 2.0
		
		if self.GUIState == STATE_INTRO:
			#Draw head
			glTranslatef(0, 0, self.zCenter)
			glRotatef(self.rotAngle, 0, 1, 0)
			glTranslatef(0, 0, -self.zCenter)
			self.headMesh.renderGL()
			self.rotAngle = self.rotAngle + 1
			self.rotAngle = self.rotAngle % 360
			time.sleep(0.01)
		elif self.GUIState == STATE_SHOWPOINTS:
			if self.GUISubstate == SHOWPOINTS_ZOOMIN:
				glTranslatef(0, 0, -self.zoom)
				self.userMesh.renderGL(drawEdges = 1, drawVerts = 1, drawNormals = 0, drawFaces = 0)
				glTranslatef(0, 0, self.zoom)
				self.zoom = self.zoom - 0.001
				time.sleep(0.01)
				if self.zoom <= self.zCenter/2:
					self.GUISubstate = SHOWPOINTS_ROTATELEFT
			elif self.GUISubstate == SHOWPOINTS_ROTATELEFT:
				print "TODO"
		self.SwapBuffers()
		self.Refresh()
	
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

class MeshViewerFrame(wx.Frame):
	(ID_LOADDATASET1, ID_LOADDATASET2, ID_SAVEDATASET, ID_SAVESCREENSHOT) = (1, 2, 3, 4)
	
	def __init__(self, parent, id, title, pos=DEFAULT_POS, size=DEFAULT_SIZE, style=wx.DEFAULT_FRAME_STYLE, name = 'GLWindow'):
		style = style | wx.NO_FULL_REPAINT_ON_RESIZE
		super(MeshViewerFrame, self).__init__(parent, id, title, pos, size, style, name)
		#Initialize the menu
		self.CreateStatusBar()
		
		self.size = size
		self.pos = pos
		
		filemenu = wx.Menu()
		menuSaveScreenshot = filemenu.Append(MeshViewerFrame.ID_SAVESCREENSHOT, "&Save Screenshot", "Save a screenshot of the GL Canvas")
		self.Bind(wx.EVT_MENU, self.OnSaveScreenshot, menuSaveScreenshot)
		menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		
		# Creating the menubar
		menuBar = wx.MenuBar()
		menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
		self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
		self.glcanvas = MeshViewerCanvas(self)
		
		#Text at the top
		titleText = wx.StaticText(self, label="Capturing Decay")
		#Buttons to go to a default view
		startButton = wx.Button(self, -1, "Let's Get Started", size = (400, 100))
		self.Bind(wx.EVT_BUTTON, self.glcanvas.startButtonHandler, startButton)
		
		#Finally add the two main panels to the sizer		
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(titleText, 0, wx.EXPAND)
		self.sizer.Add(self.glcanvas, 2, wx.EXPAND)
		self.sizer.Add(startButton, 0, wx.FIXED)
		
		self.SetSizer(self.sizer)
		self.Layout()
		self.Show()

	def OnSaveScreenshot(self, evt):
		dlg = wx.FileDialog(self, "Choose a file", ".", "", "*", wx.SAVE)
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetFilename()
			dirname = dlg.GetDirectory()
			filepath = os.path.join(dirname, filename)
			saveImageGL(self.glcanvas, filepath)
		dlg.Destroy()
		return

	def OnExit(self, evt):
		self.Close(True)
		return

class MeshViewer(object):
	def __init__(self, filename = None, ts = False, sp = "", ra = 0):
		app = wx.App()
		frame = MeshViewerFrame(None, -1, 'MeshViewer')
		frame.Show(True)
		app.MainLoop()
		app.Destroy()

if __name__ == '__main__':
	viewer = MeshViewer()
