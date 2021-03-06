#Based off of http://wiki.wxpython.org/GLCanvas
#Lots of help from http://wiki.wxpython.org/Getting%20Started
from OpenGL.GL import *
from OpenGL.GLUT import *
import wx
from wx import glcanvas

from Primitives3D import *
from PolyMesh import *
from LaplacianMesh import *
from Geodesics import *
from PointCloud import *
from Cameras3D import *
from ICP import *
from GMDS import *
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
from threading import Thread, Lock

DEFAULT_SIZE = wx.Size(1200, 800)
DEFAULT_POS = wx.Point(10, 10)
PRINCIPAL_AXES_SCALEFACTOR = 1

(STATE_INTRO, STATE_SHOWPOINTS, STATE_SHOWMESH, STATE_SHOWICP, STATE_SHOWSTRETCH, STATE_FINALMATCHING, STATE_DECAY) = (0, 1, 2, 3, 4, 5, 6)

(SHOWPOINTS_ZOOMIN, SHOWPOINTS_ROTATELEFT, SHOWPOINTS_ROTATERIGHT, SHOWPOINTS_CENTER, SHOWPOINTS_ZOOMOUT) = (0, 1, 2, 3, 4)

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
	
class ICPThread(Thread):
	def __init__(self, userMesh, targetHead, glcanvas, ICPMutex):
		Thread.__init__(self)
		self.userMesh = userMesh
		self.targetHead = targetHead
		self.glcanvas = glcanvas
		self.ICPMutex = ICPMutex
	def run(self):
		ICP_MeshToMesh(self.userMesh, self.targetHead, False, False, False, True, self.glcanvas, self.ICPMutex)

class MeshViewerCanvas(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribs = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24)
		glcanvas.GLCanvas.__init__(self, parent, -1, attribList = attribs)	
		self.context = glcanvas.GLContext(self)
		self.setText = False
		
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
		self.headMesh.loadFile('NotreDameMedium.off')
		self.headMeshLowres = PolyMesh()
		self.headMeshLowres.loadFile('NotreDameLowres.off')
		self.styrofoamHead = PolyMesh()
		self.styrofoamHead.loadFile('StyrofoamHead.off')
		self.rotAngle = 0
		self.zoom = 0
		self.rotCount = 0
		self.timelineCount = 0
		#User's face
		self.userMesh = None
		self.colorUserMesh = None
		#ICP state variables
		self.ICPTransformation = np.zeros(0)
		self.ICPMutex = Lock()
		self.ICPThread = None
		
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
	
	def drawText(self, x, y, text, size = 1, font = GLUT_BITMAP_TIMES_ROMAN_24):
		glDisable(GL_LIGHTING)
		glDisable(GL_DEPTH_TEST)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		gluOrtho2D(0, self.size[0], 0, self.size[1])
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glColor3f(1, 0, 0)
		glRasterPos2f(x, y)
		glPushMatrix()
		#for i in range(len(text)):
		#	glutBitmapCharacter(font, ord(text[i]))
		glPopMatrix()
		glEnable(GL_LIGHTING)
		glEnable(GL_DEPTH_TEST)
	
	def startButtonHandler(self, evt):
		print "Starting Face capture..."
		if not self.setText:
			self.titleText.SetLabelText("Capturing Face...")
			self.setText = True
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
		self.setText = False
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

	def handleIntroState(self):
		#Draw head
		glTranslatef(0, 0, self.zCenter)
		glRotatef(self.rotAngle, 0, 1, 0)
		glTranslatef(0, 0, -self.zCenter)
		self.headMesh.renderGL()
		self.rotAngle = self.rotAngle + 1
		self.rotAngle = self.rotAngle % 360
		#self.drawText(self.size[0]/2-50, self.size[1]-40, "A Head of Our Times")
		if not self.setText:
			self.titleText.SetLabelText("A Head of Our Times")
			self.startButton.SetLabelText("Click To Start")
			self.setText = True
		time.sleep(0.01)
		self.Refresh()
		
	def handleShowPointsState(self):
		if self.GUISubstate == SHOWPOINTS_ZOOMIN:
			if not self.setText:
				self.titleText.SetLabelText("Showing 3D Face Capture Result")
			glTranslatef(0, 0, self.zoom)
			self.userMesh.renderGL(drawEdges = 1, drawVerts = 1, drawNormals = 0, drawFaces = 0)
			glTranslatef(0, 0, -self.zoom)
			self.zoom = self.zoom + 0.005
			time.sleep(0.01)
			if self.zoom >= abs(self.zCenter/6):
				self.GUISubstate = SHOWPOINTS_ROTATELEFT
				self.rotAngle = 0
				self.rotCount = 0
		elif self.GUISubstate == SHOWPOINTS_ROTATELEFT:
			self.setText = True
			glTranslatef(0, 0, self.zCenter + self.zoom)
			glRotatef(self.rotAngle, 0, 1, 0)
			glTranslatef(0, 0, -self.zCenter)
			if self.rotCount == 0:
				self.userMesh.renderGL(drawEdges = 1, drawVerts = 1, drawNormals = 0, drawFaces = 0)
			else:
				self.userMesh.renderGL(drawEdges = 0, drawVerts = 0, drawNormals = 0, drawFaces = 1, lightingOn = False)
			self.rotAngle = self.rotAngle - 1
			if self.rotAngle < -60:
				self.GUISubstate = SHOWPOINTS_ROTATERIGHT
			time.sleep(0.01)
		elif self.GUISubstate == SHOWPOINTS_ROTATERIGHT:
			glTranslatef(0, 0, self.zCenter + self.zoom)
			glRotatef(self.rotAngle, 0, 1, 0)
			glTranslatef(0, 0, -self.zCenter)
			if self.rotCount == 0:
				self.userMesh.renderGL(drawEdges = 1, drawVerts = 1, drawNormals = 0, drawFaces = 0)
			else:
				self.userMesh.renderGL(drawEdges = 0, drawVerts = 0, drawNormals = 0, drawFaces = 1, lightingOn = False)
			self.rotAngle = self.rotAngle + 1
			if self.rotAngle > 60:
				self.rotCount = self.rotCount + 1
				if self.rotCount >= 2:
					self.GUISubstate = SHOWPOINTS_CENTER
				else:
					self.GUISubstate = SHOWPOINTS_ROTATELEFT
			time.sleep(0.01)
		elif self.GUISubstate == SHOWPOINTS_CENTER:
			glTranslatef(0, 0, self.zCenter + self.zoom)
			glRotatef(self.rotAngle, 0, 1, 0)
			glTranslatef(0, 0, -self.zCenter)
			self.userMesh.renderGL(drawEdges = 0, drawVerts = 0, drawNormals = 0, drawFaces = 1, lightingOn = False)
			self.rotAngle = self.rotAngle - 1
			if self.rotAngle <= 0:
				self.GUISubstate = SHOWPOINTS_ZOOMOUT
			time.sleep(0.01)
		elif self.GUISubstate == SHOWPOINTS_ZOOMOUT:
			glTranslatef(0, 0, self.zoom)
			self.userMesh.renderGL(drawEdges = 0, drawVerts = 0, drawNormals = 0, drawFaces = 1, lightingOn = False)
			glTranslatef(0, 0, -self.zoom)
			self.zoom = self.zoom - 0.005
			time.sleep(0.01)
			if self.zoom <= 0:
				self.GUIState = STATE_SHOWICP
				self.setText = False
				self.bbox = self.styrofoamHead.getBBox()
				self.camera.centerOnBBox(self.bbox, theta = -math.pi/2, phi = math.pi/2)
				#Get the mesh's renderbuffer ready before the thread starts so that no ICP frames are missed
				self.styrofoamHead.renderGL(drawEdges = 0, drawVerts = 0, drawNormals = 0, drawFaces = 1)
				self.ICPThread = ICPThread(self.userMesh, self.styrofoamHead, self, self.ICPMutex)
				self.ICPThread.start()
		self.drawText(self.size[0]/2-50, self.size[1]-40, "Showing Captured Face")
		self.Refresh()
	
	def transplantColors(self):
		perms = np.random.permutation(len(self.userMesh.vertices))
		N = min(1000, len(perms))
		VX = np.zeros((N, 3))
		CX = np.zeros((N, 3))
		#Randomly subsample points for speed
		
		for i in range(N):
			idx = perms[i]
			P = self.userMesh.vertices[idx].pos
			C = self.userMesh.vertices[idx].color
			VX[i, :] = np.array([P.x, P.y, P.z])
			CX[i, :] = C
		VX = transformPoints(self.ICPTransformation, VX)
		self.titleText.SetLabelText("Placing Colors on Head")
		print "Getting initial guess of point positions..."
		ts, us = getInitialGuessClosestPoints(VX, self.styrofoamHead)
		print "Finished initial guess of point positions"
		self.colorUserMesh = transplantColorsLaplacianUsingBarycentric(self.styrofoamHead, CX, ts, us)
	
	def handleICPState(self):
		glPushMatrix()
		if self.ICPTransformation.shape[0] > 0:
			glMultMatrixd(self.ICPTransformation.transpose().flatten())
		self.userMesh.renderGL(drawEdges = 0, drawVerts = 0, drawNormals = 0, drawFaces = 1, lightingOn = False)
		glPopMatrix()
		glColor3f(0.7, 0.7, 0.7)
		self.styrofoamHead.renderGL(drawEdges = 0, drawVerts = 0, drawNormals = 0, drawFaces = 1, lightingOn = True)
		#self.drawText(self.size[0]/2-50, self.size[1]-40, "Aligning Face with Statue...")
		if not self.setText:
			self.titleText.SetLabelText("Performing Rigid Alignment to Statue")
			self.setText = True
		if not self.ICPThread.isAlive():
			print "Alignment finished"
			print "Transplanting colors..."
			self.transplantColors()
			print "Finished Transplanting colors"
			self.setText = False
			self.GUIState = STATE_DECAY
			self.timelineState = 0
			self.bbox = self.colorUserMesh.getBBox()
			self.camera.centerOnBBox(self.bbox, theta = -math.pi/2, phi = math.pi/2)
	
	def handleDecayState(self):
		if self.timelineState > 40:
			#Render the head in its current form
			self.colorUserMesh.renderGL(drawEdges = 0, drawVerts = 0, drawNormals = 0, drawFaces = 1, lightingOn = True)				
		
		if self.timelineState == 0:
			titleFont = wx.Font(24, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
			self.titleText.SetFont(titleFont)
		if self.timelineState <= 20:
			#TODO: Include Images here
			self.titleText.SetLabelText("1180 - 1223: Paris becomes capital of French Kingdom")
			time.sleep(0.05)
			self.Refresh()
		elif self.timelineState <= 40:
			self.titleText.SetLabelText("1163: Construction of Notre Dame Cathedral Begins")
			time.sleep(0.05)
			self.Refresh()
		elif self.timelineState <= 60:
			self.titleText.SetLabelText("1245 - 1258: Remodling of North transept and addition of the Virtue")
			time.sleep(0.1)
		elif self.timelineState < 120:
			year = int(np.round((self.timelineState - 60)*(1793 - 1258)/60.0 + 1258))
			self.titleText.SetLabelText("%i: Virtue in Situ on Cathedral Facade"%year)
			#Dampen the colors
			for v in self.colorUserMesh.vertices:
				C = v.color
				meanC = sum(C)/float(len(C))
				v.color = [c - (c - meanC)*0.025 for c in C]
			self.colorUserMesh.needsDisplayUpdate = True
		else:
			if self.timelineState == 121:
				self.titleText.SetLabelText("1793: French Revolution and the Iconoclasm/Vandalism")
			#TODO: Rotate head slightly to left, fix chunks
			if self.timelineState == 120:
				USINGLAPLACIAN = False
				self.titleText.SetLabelText("1793: French Revolution Iconoclasm: Decapitation Imminent...")
				#Make some dents
				perms = np.random.permutation(len(self.colorUserMesh.vertices))
				print "CHUNKING"
				constraints = []
				chunks = 0
				for i in range(0, 20):
					idx = perms[i]
					V = self.colorUserMesh.vertices[idx]
					if USINGLAPLACIAN:
						N = V.getNormal()
						#if np.abs(N.z) < 0.8:
						#	continue
						chunks = chunks + 1
						chunkSize = 0.05*np.random.rand(1)[0]
						P = V.pos - chunkSize*Vector3D(0, 0, -1)
						constraints.append((idx, P))
						otherVerts = V.getVertexNeighbors()
						for V2 in otherVerts:
							P = V2.pos - chunkSize*0.5*Vector3D(0, 0, -1)
							constraints.append((V2.ID, P))
					else:
						P = V.pos
						randDiff = 0.02*np.random.rand(1)[0]
						P = P - randDiff*V.getNormal()
						V.pos = P
						for V2 in V.getVertexNeighbors():
							P = V2.pos - 0.5*randDiff*V2.getNormal()
							V2.pos = P
				if USINGLAPLACIAN:
					self.colorUserMesh.solveVertexPositionsWithConstraints(constraints)
				self.colorUserMesh.needsDisplayUpdate = True
				print "There were %i chunks"%chunks
		self.timelineState = self.timelineState + 1
		self.Refresh()
	
	def handleShowStretchState(self):
		#TODO: Finish this
		self.GUIState = STATE_SHOWSTRETCH
		self.Refresh()
	
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
			self.handleIntroState()
		elif self.GUIState == STATE_SHOWPOINTS:
			self.handleShowPointsState()
		elif self.GUIState == STATE_SHOWICP:
			self.handleICPState()
		elif self.GUIState == STATE_DECAY:
			self.handleDecayState()
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

class MeshViewerFrame(wx.Frame):
	(ID_LOADDATASET1, ID_LOADDATASET2, ID_SAVEDATASET, ID_SAVESCREENSHOT) = (1, 2, 3, 4)
	
	def __init__(self, parent, id, title, pos=DEFAULT_POS, size=DEFAULT_SIZE, style=wx.DEFAULT_FRAME_STYLE, name = 'GLWindow'):
		style = style | wx.NO_FULL_REPAINT_ON_RESIZE
		super(MeshViewerFrame, self).__init__(parent, id, title, pos, size, style, name)
		#Initialize the menu
		self.CreateStatusBar()
		self.SetBackgroundColour((0, 0, 0))
		
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
		titleFont = wx.Font(46, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		self.glcanvas.titleText = wx.StaticText(self, label="Capturing Decay")
		self.glcanvas.titleText.SetLabelText("A Head of Our Times")
		self.glcanvas.titleText.SetFont(titleFont)
		self.glcanvas.titleText.SetBackgroundColour((0, 0, 0))
		self.glcanvas.titleText.SetForegroundColour((255, 255, 255))
		#Buttons to go to a default view
		self.glcanvas.startButton = wx.Button(self, -1, "Click To Start", size = (400, 100))
		self.glcanvas.startButton.SetBackgroundColour((127, 127, 127))
		self.glcanvas.startButton.SetForegroundColour((0, 0, 0))
		buttonFont = wx.Font(46, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		self.glcanvas.startButton.SetFont(buttonFont)
		self.Bind(wx.EVT_BUTTON, self.glcanvas.startButtonHandler, self.glcanvas.startButton)
		
		#Finally add the two main panels to the sizer		
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.glcanvas.titleText, 0, wx.FIXED)
		self.sizer.Add(self.glcanvas, 2, wx.EXPAND)
		self.sizer.Add(self.glcanvas.startButton, 0, wx.FIXED)
		
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
