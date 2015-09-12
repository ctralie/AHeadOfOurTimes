#Implement the technique in the Sumner/Popovic paper
#"Deformation Transfer for Triangle Meshes"
import numpy as np
from scipy import sparse
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import lsqr, cg, eigsh
from scipy.spatial import Delaunay
import scipy.io as sio
from scipy.sparse.linalg import spsolve, bicg

#Iterative closest points
def getRigidTransformation(Points, TargetPoints):
    dim = Points.shape[1]
    meanP = np.mean(Points, 0)
    meanT = np.mean(TargetPoints, 0)
    P = Points - meanP
    T = TargetPoints - meanT
    H = np.dot(P.T, T)
    U, s, V = np.linalg.svd(H)
    R = np.eye(dim+1)
    R[0:dim, 0:dim] = np.dot(V.T, U.T)
    #Transformation order:
    #1: Move the point set so it's centered on the centroid
    #2: Rotate the point set by the calculated rotation
    #3: Move the point set so it's centered on the target centroid
    T1 = np.eye(dim+1)
    T1[0:dim, -1] = -meanP.T
    T2 = np.eye(dim+1)
    T2[0:dim, -1] = meanT
    T = np.dot(T2, np.dot(R, T1))
    return T
    

#Return a matrix whose columns span a 3D parallelpiped in line
#with the given triangle in V
def getVRelMatrix(V):
    V4 = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
    V4 = V[:, 0] + V4/(np.dot(V4, V4)**0.25)
    V1 = np.reshape(V[:, 0].copy(), (3, 1))
    V[:, 0:2] = V[:, 1:3].copy()
    V[:, 2] = V4.copy()
    VRet = V - np.tile(V1, (1, 3))
    return VRet

class DeformationMesh(object):
    #faces, number of vertices
    def __init__(self, faces, NVertices):
        self.faces = faces
        self.NVertices = NVertices
        self.A = np.array([])
    
    #targetPos is an NVertices x 3 array of target positions
    def setupMatrix(self, targetPos):
        I = [] #I indices
        J = [] #J indices
        M = [] #Matrix values
        for i in range(self.faces.shape[0]):
            F = self.faces[i, :]
            V = (targetPos[F, :].copy()).T
            V = getVRelMatrix(V)
            V = np.linalg.inv(V) #As long as there are no degenerate triangles this should work
            idx = [F[1], F[2], self.NVertices+i, F[0]] #V2, V3, V4, V1
            v4Elem = np.sum(V, 0)
            for j in range(3):
                I = I + [3*i+j]*4
                J = J + idx
                M = M + [V[0, j], V[1, j], V[2, j], -np.sum(V[:, j])]
        self.A = sparse.coo_matrix((M, (I, J)), shape=(self.faces.shape[0]*3,self.faces.shape[0]+self.NVertices)).tocsr()
        self.AT = self.A.T
        self.ATA = self.AT.dot(self.A)

    #Given a source mesh with an initial position and a final position
    #solve for the vertex coordinates that do the analogous deformation
    #for the target mesh
    def solveForVertices(self, SInitial, SFinal):
        S = np.zeros((3*self.faces.shape[0], 3))
        for i in range(self.faces.shape[0]):
            F = self.faces[i, :]
            VI = getVRelMatrix(SInitial[F, :].T)
            VF = getVRelMatrix(SFinal[F, :].T)
            thisS = np.dot(VI, np.linalg.inv(VF))
            S[i*3:(i+1)*3, :] = thisS.T
        S = csr_matrix(S)
        Verts = spsolve(self.ATA, self.AT.dot(S))
        Verts = Verts.toarray()
        return Verts[0:self.NVertices, :] #Ignore the perpendicular vertices

if __name__ == '__main__':
    fin = open('candideFaces.txt', 'r')
    faces = np.array( [ [int(a) for a in x.split()] for x in fin.readlines() ], dtype = np.int32)
    fin.close()
    
    StatueInfo = sio.loadmat('StatueInfo.mat')
    
    #Not all of the vertices in the candide model are used so do
    #the appropriate substitution
    fin = open('VerticesUsed.txt', 'r')
    VerticesUsed = np.array( [int(a) for a in fin.readlines()] )
    fin.close()
    for i in range(len(VerticesUsed)):
        faces[faces == VerticesUsed[i]] = i
    
    M = DeformationMesh(faces, len(VerticesUsed))
    #The target mesh is the statue so we want its neutral face to be
    #the initial mesh
    M.setupMatrix(StatueInfo['NeutralPos'])
    
    #Load in my face neutral and another expression
    testName = 'BasicExample'
    NFrames = 300
    fin = open("%s/0.txt"%testName, 'r')
    lines = fin.readlines()
    SInitial = np.array( [ [float(a) for a in x.split()] for x in lines[1:] ] )
    SInitial = SInitial[VerticesUsed, :]
    fin.close()
    
    for i in range(NFrames):
        print "Transfering motion to mesh %i..."%i
        fin = open("%s/%i.txt"%(testName, i), 'r')
        lines = fin.readlines()
        SFinal = np.array( [ [float(a) for a in x.split()] for x in lines[1:] ] )
        SFinal = SFinal[VerticesUsed, :]
        fin.close()
        
        #Do ICP to align SFinal to SInitial as best as possible
        T = getRigidTransformation(SFinal, SInitial)
        VNew = np.concatenate((SFinal, np.ones((SFinal.shape[0], 1))), 1)
        VNew = np.dot(T, VNew.T)
        SFinal = VNew[0:3, :].T
        
        V = M.solveForVertices(SInitial, SFinal)
        VOut = np.zeros((121, 3))
        VOut[VerticesUsed, :] = V
        fout = open("%s/Statue%i.txt"%(testName, i), 'w')
        for i in range(VOut.shape[0]):
            fout.write("%g %g %g\n"%(VOut[i, 0], VOut[i, 1], VOut[i, 2]))
        fout.close()
