import numpy as np
import numpy.linalg as linalg
from scipy.spatial import Delaunay
import os

CONSISTENT_NORMALS = True

#u v x y z r g b
def extractMeshFiles():
	fin = open("temp.txt")
	lines = fin.readlines()
	fin.close()
	N = len(lines)
	
	#Compute the Delaunay Triangulation on the (u, v)
	#coordinates of the points
	points = np.zeros((N, 2))
	for i in range(N):
		vals = lines[i].split(" ")
		#points[i, 0] = float(vals[0])
		#points[i, 1] = float(vals[1])
		points[i, 0] = float(vals[2])
		points[i, 1] = float(vals[3])
	tri = Delaunay(points)
	M = int(tri.simplices.shape[0])
	
	print "%i points, %i triangles\n"%(N, M)
	
	offFile = open('out.off', 'w')
	offFile.write("OFF\n")
	offFile.write("%i %i 0\n"%(N, M))
	
	plyFile = open('out.ply', 'w')
	plyFile.write('ply\n');
	plyFile.write('format ascii 1.0\n')
	plyFile.write('element vertex %i\n'%N)
	plyFile.write('property float x\nproperty float y\nproperty float z\n')
	plyFile.write('property uchar red\nproperty uchar green\nproperty uchar blue\n')
	plyFile.write('element face %i\n'%M)
	plyFile.write('property list uchar int vertex_indices\n')
	plyFile.write('end_header\n')
	
	
	#Output the points to the OFF file and PLY file
	for i in range(N):
		vals = lines[i].split(" ")
		#x y z r g b
		vals = vals[2:]
		xyz = [float(a) for a in vals[0:3]]
		xyz[2] = -xyz[2] #Compensate for coordinate system
		rgb = [int(a) for a in vals[3:6]]
		rgbfloat = [float(a)/255.0 for a in rgb]
		offFile.write("%s %s %s %g %g %g\n"%(tuple(xyz + rgbfloat)))
		plyFile.write("%s %s %s %i %i %i\n"%(tuple(xyz + rgb)))
	
	#Output the triangles to the OFF file and PLY file
	for i in range(M):
		[a, b, c] = tri.simplices[i, :]
		if CONSISTENT_NORMALS:
			D = np.ones((3, 3))
			D[1:, 0] = points[a, :]
			D[1:, 1] = points[b, :]
			D[1:, 2] = points[c, :]
			#Make sure the triangle faces have consistent normals
			if linalg.det(D) > 0:
				[a, b, c] = [c, b, a]
		triString = "3 %i %i %i\n"%(a, b, c)
		offFile.write(triString)
		plyFile.write(triString)
	
	offFile.close()
	plyFile.close()