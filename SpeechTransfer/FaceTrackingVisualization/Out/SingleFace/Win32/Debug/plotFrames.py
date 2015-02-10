#Based off of http://wiki.wxpython.org/GLCanvas
#Lots of help from http://wiki.wxpython.org/Getting%20Started
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.raw import GL
from OpenGL.GL import shaders
from OpenGL.arrays import vbo
import wx
from wx import glcanvas

from Cameras3D import *
from sys import exit, argv
import random
import numpy as np
import scipy.io as sio
from scipy.io import wavfile
import os
import math
import time
import pygame.mixer
import time
import matplotlib.pyplot as plt

try:
    from PIL.Image import open as imgopen
except ImportError, err:
    from Image import open as imgopen

DEFAULT_SIZE = wx.Size(1200, 800)
DEFAULT_POS = wx.Point(10, 10)

WAVEFILENAME = "out.wav"
NPOINTS = 121

def loadTexture(filename):
	im = imgopen(filename)
	try:
		im = im.convert('RGB')
		ix, iy, image = im.size[0], im.size[1], im.tostring("raw", "RGBA", 0, -1)
	except SystemError:
		ix, iy, image = im.size[0], im.size[1], im.tostring("raw", "RGBX", 0, -1)
	assert ix*iy*4 == len(image), """Unpacked image size for texture is incorrect"""
	
	texID = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, texID)
	glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
	glTexImage2D(GL_TEXTURE_2D, 0, 3, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, image)
	return texID

class FaceTalkingCanvas(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribs = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24)
		glcanvas.GLCanvas.__init__(self, parent, -1, attribList = attribs)	
		self.context = glcanvas.GLContext(self)
		
		self.parent = parent
		#Camera state variables
		self.size = self.GetClientSize()
		self.camera = MousePolarCamera(self.size.width, self.size.height)
		
		#Main state variables
		self.MousePos = [0, 0]
		self.initiallyResized = False
		
		self.bbox = np.array([ [1, 1, 1], [-1, -1, -1] ])
		random.seed()
		
		#Point cloud and playing information
		self.displayCount = 0
		self.SampleDelays = np.array([])
		self.NFrames = 0
		self.currFrame = 0
		self.PointClouds = []
		self.Playing = False
		self.PlayIDX = 0
		
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
		
		#Load in candide mesh information and store in an index buffer
		fin = open('candideFaces.txt', 'r')
		indices = np.array( [ [int(a) for a in x.split()] for x in fin.readlines() ], dtype = np.int32)
		self.candideFaces = vbo.VBO(indices, target=GL_ELEMENT_ARRAY_BUFFER)
		fin.close()
		fin = open('candideTexCoords.txt', 'r')
		self.texCoords = vbo.VBO(np.array( [ [float(a) for a in x.split()] for x in fin.readlines() ], dtype = np.float32))
		fin.close()
		self.texID = -1
	
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

	def startAnimation(self, evt):
		#Figure out sampling rate of wave file
		self.Fs, X = wavfile.read(WAVEFILENAME)
		
		#Figure out the offset based on the timestamp and the number of recorded samples
		fin = open("captureTimeFile.txt")
		lines = fin.readlines()
		audioTimestamp = float(lines[0].split()[0])	
		actualAudioTime = float(lines[0].split()[1])/(16000.0*4*4) #4 channels 32 bits per channel
		OFFSET = audioTimestamp - actualAudioTime
		print "OFFSET = %g"%OFFSET
		
		#Load in all of the point clouds
		self.PointClouds = []
		self.AllPoints = np.zeros((self.NFrames, NPOINTS, 3))
		self.SampleDelays = np.zeros(self.NFrames)
		for i in range(self.NFrames):
			fin = open("%i.txt"%i, 'r')
			lines = fin.readlines()
			self.SampleDelays[i] = float(lines[0]) - OFFSET
			print self.SampleDelays[i]
			lines = lines[1:]
			X = np.zeros((len(lines), 3))
			for k in range(len(lines)):
				X[k, :] = [1000.0*float(a) for a in lines[k].split()]
				self.AllPoints[i, k, :] = X[k, :]
			self.PointClouds.append(vbo.VBO(np.array(X, dtype='float32')))
			#TODO: Is there a memory leak adding vertex buffers this way?
			fin.close()
		
		if len(self.SampleDelays) > 0:
			X = self.AllPoints
			mins = [np.max(X[:, :, 0]), np.max(X[:, :, 1]), np.max(X[:, :, 2])]
			maxs = [np.min(X[:, :, 0]), np.min(X[:, :, 1]), np.min(X[:, :, 2])]
			self.bbox = np.array([maxs, mins])
			self.camera.centerOnBBox(self.bbox, math.pi/2, math.pi/2)
			print "Playing %s"%WAVEFILENAME
			self.Playing = True
			self.PlayIDX = 0
			pygame.mixer.quit()
			print "Starting mixer at %i"%self.Fs
			pygame.mixer.init(frequency = self.Fs)
			s = pygame.mixer.Sound(WAVEFILENAME)
			s.play()
			self.startTime = time.time()
			self.Playing = True
			self.Refresh()

	def repaint(self):
		#Set up projection matrix
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		farDist = 3*np.sqrt(np.sum( (self.camera.eye - np.mean(self.bbox, 0))**2 ))
		nearDist = farDist/50.0
		gluPerspective(180.0*self.camera.yfov/np.pi, float(self.size.x)/self.size.y, nearDist, farDist)
		
		#Set up modelview matrix
		self.camera.gotoCameraFrame()	
		glClearColor(0.0, 0.0, 0.0, 0.0)
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		
		if len(self.PointClouds) > 0:
			if self.texID == -1:
				self.texID = loadTexture("CandideTexture.png")
			
			glDisable(GL_LIGHTING)
			glPointSize(3)
			if self.Playing:
				self.endTime = time.time()
				dT = self.endTime - self.startTime
				while dT > self.SampleDelays[self.PlayIDX]:
					self.PlayIDX = self.PlayIDX + 1
					if self.PlayIDX == self.NFrames - 1:
						self.Playing = False
				self.Refresh()
			glEnable(GL_TEXTURE_2D)
			glEnableClientState(GL_TEXTURE_COORD_ARRAY)
			glEnableClientState(GL_VERTEX_ARRAY)
			
			glBindTexture(GL_TEXTURE_2D, self.texID)
			self.PointClouds[self.PlayIDX].bind()
			
			glVertexPointerf( self.PointClouds[self.PlayIDX] )
			
			self.texCoords.bind()
			glTexCoordPointerf( self.texCoords )
			self.PointClouds[self.PlayIDX].unbind()
			self.candideFaces.bind()
			glDrawElements(GL_TRIANGLES, 3*len(self.candideFaces), GL_UNSIGNED_INT, None)
			#glDrawArrays(GL_POINTS, 0, NPOINTS)
			
			glDisableClientState(GL_VERTEX_ARRAY)
			glDisableClientState(GL_TEXTURE_COORD_ARRAY)
			
		self.SwapBuffers()
	
	def initGL(self):		
		glutInit('')
		glEnable(GL_NORMALIZE)
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

class FaceTalkingFrame(wx.Frame):
	(ID_LOADSONGFILE, ID_LOADMATFILE, ID_SAVESCREENSHOT, ID_ARCLENGTHDOWNSAMPLE, ID_DENSITYTHRESHOLD, ID_SAVEPOINTCLOUD) = (1, 2, 3, 4, 5, 6)
	(COLORTYPE_TIME, COLORTYPE_DENSITY, COLORTYPE_HKS) = (1, 2, 3)	
	
	def __init__(self, parent, id, title, pos=DEFAULT_POS, size=DEFAULT_SIZE, style=wx.DEFAULT_FRAME_STYLE, name = 'GLWindow', NFrames = 0):
		style = style | wx.NO_FULL_REPAINT_ON_RESIZE
		super(FaceTalkingFrame, self).__init__(parent, id, title, pos, size, style, name)
		#Initialize the menu
		self.CreateStatusBar()
		
		#Sound variables
		self.soundSamples = np.array([])

		self.Fs = 22050
		
		self.size = size
		self.pos = pos
		
		filemenu = wx.Menu()
		menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
		self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
		
		# Creating the menubar.
		menuBar = wx.MenuBar()
		menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
		self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
		self.glcanvas = FaceTalkingCanvas(self)
		self.glcanvas.NFrames = NFrames
		
		self.rightPanel = wx.BoxSizer(wx.VERTICAL)
		
		#Buttons to go to a default view
		animatePanel = wx.BoxSizer(wx.VERTICAL)
		self.rightPanel.Add(wx.StaticText(self, label="Animation Options"), 0, wx.EXPAND)
		self.rightPanel.Add(animatePanel, 0, wx.EXPAND)
		playButton = wx.Button(self, -1, "Play")
		self.Bind(wx.EVT_BUTTON, self.glcanvas.startAnimation, playButton)
		animatePanel.Add(playButton, 0, wx.EXPAND)
					
		
		#Finally add the two main panels to the sizer		
		self.sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(self.glcanvas, 2, wx.EXPAND)
		self.sizer.Add(self.rightPanel, 0, wx.EXPAND)
		
		self.SetSizer(self.sizer)
		self.Layout()
		self.Show()

	def OnExit(self, evt):
		self.Close(True)
		return

class FaceTalking(object):
	def __init__(self, NFr):
		app = wx.App()
		frame = FaceTalkingFrame(None, -1, 'FaceTalking', NFrames = NFr)
		frame.Show(True)
		app.MainLoop()
		app.Destroy()

if __name__ == '__main__':
	if len(argv) < 2:
		print "Usage: python plotFrames.py <NFrames>"
		exit(0)
	app = FaceTalking(int(argv[1]))
