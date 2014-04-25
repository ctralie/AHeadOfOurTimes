from Primitives3D import *
from PolyMesh import *
from ICP import *
from sys import argv, exit
import numpy as np
import numpy.linalg as linalg
from scipy.spatial import Delaunay
import matplotlib.pyplot as plt

def findHole(mesh):
	origEdges = mesh.edges[:]
	for e in origEdges:
		if e.numAttachedFaces():
			loop = [e.v1, e.v2]
			finished = False
			while not finished:
				foundNext = False
				for v in loop[-1].getVertexNeighbors():
					if v is loop[-2]:
						#Make sure it doesn't accidentally back up
						continue
					elif v is loop[0]:
						#It's looped back on itself so we're done
						finished = True
					else:
						e = getEdgeInCommon(loop[-1], v)
						if not e:
							print "Warning: Edge not found in common while trying to trace hole boundary"
							finished = True
							break
						elif e.numAttachedFaces() == 1:
							foundNext = True
							loop.append(v)
							break
				if not foundNext and not finished:
					print "Warning: Unable to close hole"
					break
			print "Found hole of size %i"%len(loop)
			return loop

if __name__ == '__main__':
	if len(argv) < 3:
		print "Usage: AddFaceBack [inputMesh] [outputMesh]"
		exit(0)
	mesh = PolyMesh()
	mesh.loadFile(argv[1])
	hole = findHole(mesh)
	(Axis1, Axis2, Axis3, maxProj, minProj, axes) = mesh.getPrincipalAxes()
	Centroid = mesh.getCentroid()


	#Copy over the hole boundary points to a numpy array
	NH = len(hole)
	VH = np.zeros((NH, 3))
	for i in range(NH):
		thisP = hole[i].pos
		VH[i, :] = np.array([thisP.x, thisP.y, thisP.z])
	#Transform the mesh and the the coordinate system of the principal axes of the mesh
	#where the Z coordinate can be ignored (since it's the axis of least variation)
	Trans = np.eye(4)
	Trans[0, 3] = -Centroid.x
	Trans[1, 3] = -Centroid.y
	Trans[2, 3] = -Centroid.z
	Rot = np.eye(4)
	Rot[0:3, 0:3] = axes.transpose()
	T = Rot.dot(Trans)
	VH2D = transformPoints(T, VH)
	VH2D = VH2D[:, 0:2]
	[minx, miny] = VH2D.min(0)
	[maxx, maxy] = VH2D.max(0)
	ux, uy = np.mgrid[minx:maxx:6j, miny:maxy:6j]
	ux = ux.flatten()
	uy = uy.flatten()
	uindices = []
	tri = Delaunay(VH2D)
	Vs = tri.vertices
	for i in range(len(ux)):
		#print "\n"
		#Check the CCW of this point against every point on the hole
		isInside = False
		for j in range(Vs.shape[0]):
			[i1, i2, i3] = Vs[j]
			D1 = np.array([ [1, ux[i], uy[i]], [1, VH2D[i1, 0], VH2D[i1, 1]], [1, VH2D[i2, 0], VH2D[i2, 1]] ])
			D2 = np.array([ [1, ux[i], uy[i]], [1, VH2D[i2, 0], VH2D[i2, 1]], [1, VH2D[i3, 0], VH2D[i3, 1]] ])
			D3 = np.array([ [1, ux[i], uy[i]], [1, VH2D[i3, 0], VH2D[i3, 1]], [1, VH2D[i1, 0], VH2D[i1, 1]] ])
			det1 = np.sign(linalg.det(D1))
			det2 = np.sign(linalg.det(D2))
			det3 = np.sign(linalg.det(D3))
			dets = np.array([det1, det2, det3])
			if abs(dets.sum()) == (3 - (dets == 0).sum()):
				isInside = True
				break
		if isInside:
			uindices.append(i)
	
	#Get the radii of the elipsoid around the principal axes
	rx = 0.5*(maxProj[0] - minProj[0])
	cx = Centroid.x
	ry = 0.5*(maxProj[1] - minProj[1])
	cy = Centroid.y
	rz = 0.5*(maxProj[2] - minProj[2])
	R = max(rx, ry, rz)
	cz = Centroid.z
	[cx, cy, cz, hom] = T.dot([cx, cy, cz, 1])
	NewPointsObj = []
	uz = []
	for i in range(len(ux)):
		x = ux[i]
		y = uy[i]
		z = -R*(1 - (x - cx)**2/R**2 - (y - cy)**2/R**2)
		uz.append(cz + z - 0.02)
	uz = np.array(uz)

	print "There are %i new points inside of hole"%len(uindices)
	NewPoints = np.zeros((len(uindices), 3))
	NewPoints[:, 0] = ux[uindices]
	NewPoints[:, 1] = uy[uindices]
	NewPoints[:, 2] = uz[uindices]
	NewPoints3D = transformPoints(linalg.inv(T), NewPoints)
	NewPointsObj = []
	#Add the new vertices to the mesh
	for i in range(NewPoints.shape[0]):
		P = Point3D(NewPoints3D[i, 0], NewPoints3D[i, 1], NewPoints3D[i, 2])
		NewPointsObj.append(mesh.addVertex(P))
	
	#Do a Delaunay Triangulation of the new points and the points on the boundary
	#to figure out what the triangles should be
	NHole = VH2D.shape[0]
	AllPoints = np.concatenate((VH2D, NewPoints[:, 0:2]))
	MeshPoints = hole + NewPointsObj
#	tri = Delaunay(AllPoints)
#	Vs = tri.vertices
#	#Add the simplices
#	for i in range(len(Vs)):
#		[i1, i2, i3] = Vs[i]
#		mesh.addFace([MeshPoints[i1], MeshPoints[i2], MeshPoints[i3]])
	tri = Delaunay(NewPoints[:, 0:2])
	Vs = tri.vertices
	for i in range(len(Vs)):
		[i1, i2, i3] = Vs[i]
		mesh.addFace([NewPointsObj[i1], NewPointsObj[i2], NewPointsObj[i3]])
	
	#Plot everything
	plt.hold(True)
	
	for i in range(len(Vs)):
		[i1, i2, i3] = Vs[i]
		plt.plot([AllPoints[i1, 0], AllPoints[i2, 0], AllPoints[i3, 0], AllPoints[i1, 0]], [AllPoints[i1, 1], AllPoints[i2, 1], AllPoints[i3, 1], AllPoints[i1, 1]], 'r')	
	plt.plot(VH2D[:, 0], VH2D[:, 1], 'b')
	plt.plot(NewPoints[:, 0], NewPoints[:, 1], 'g.')
	plt.show()
	
	mesh.saveFile(argv[2])
