import numpy as np
from scipy.spatial import Delaunay
import os

#u v x y z r g b
if __name__ == '__main__':
	os.popen3("SingleFace")
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
	
	fout = open('out.off', 'w')
	fout.write("OFF\n")
	fout.write("%i %i 0\n"%(N, M))
	#Output the points to the OFF file
	for i in range(N):
		vals = lines[i].split(" ")
		#x y z r g b
		vals = vals[2:]
		fout.write( ("%s "*len(vals)).strip()%tuple(vals) )
	
	#Output the triangles to the OFF file
	for i in range(M):
		simplex = tri.simplices[i, :]
		fout.write("3 %i %i %i\n"%(simplex[0], simplex[1], simplex[2]))
	
	fout.close()