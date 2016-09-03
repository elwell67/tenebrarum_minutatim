import sys, math, numpy

def A(a):
    return numpy.array(a)

CARDINAL_BASIS = [ A([1,0,0]), A([0,1,0]), A([0,0,1]), A([-1,0,0]), A([0,-1,0]), A([0,0,-1]) ]

def decomp_vector_from_angle(theta):
    X = numpy.matrix([math.sqrt(3)/2.0, math.cos(theta)/2.0, math.sin(theta)/2.0])
    # nudged toward X-axis, choices too ambiguous otherwise
    # X = X + numpy.matrix([0.000000001, -0.0000000005, -0.0000000005])
    # X = X / numpy.linalg.norm(X)
    return X

# Six evenly spaced angles
DECOMPOSITION_ANGLES = [0.0, math.pi/3.0, 2.0*math.pi/3.0, math.pi, 4.0*math.pi/3.0, 5.0*math.pi/3.0]
# Six evenly spaced vectors about the x-axis
decomposition_vectors_about_x_axis = map(decomp_vector_from_angle, DECOMPOSITION_ANGLES)

def level_to_radians(level):
    return math.pi / math.pow(2.0, level + 2)
        
 
def skew_symetric_cross(v):
    return numpy.matrix( [ [0, -v[2], v[1]] , [v[2], 0, -v[0]] , [-v[1], v[0], 0] ])

# http://math.stackexchange.com/questions/180418/calculate-rotation-matrix-to-align-vector-a-to-vector-b-in-3d
def rot_x_matrix(current_vector):
    V = numpy.cross(current_vector, CARDINAL_BASIS[0])
    s = numpy.linalg.norm(V)
    c = numpy.inner(current_vector, CARDINAL_BASIS[0])
    if s < 0.00000000000000000001:
        # These responses assume CARDINAL_BASIS[0] == [ 1.0,  0.0,  0.0]
        if c < 0:
            return numpy.matrix([[ -1.0,  0.0,  0.0], [ 0.0,  1.0,  0.0], [ 0.0,  0.0,  1.0]])
        else:
            return numpy.matrix([[ 1.0,  0.0,  0.0], [ 0.0,  1.0,  0.0], [ 0.0,  0.0,  1.0]])
    Vx = skew_symetric_cross(V)
    R = Vx + numpy.identity(3) + (numpy.dot(Vx, Vx) * ((1 - c) / (s * s)))
    return R

# Generate one of six evenly spaced vectors oriented in a circle on the unit sphere about current_vector    
#     To make the math "obvious" we compute the new vector about the X axis and then use a
#     rotation matrix to orient this vector about current_vector
#
#     TODO:  Optimize end of this routine:
#     The approach of iteratively sub-dividing the result vector towards the current_vector
#     gives the correct result.  I am sure there is a more direct approach which would again
#     be produced by rotating the result vector towards the current_vector in one step.
def decomposition_vector(current_vector, level, letter):   
    idx = ord(letter) - ord('0')
    
    if idx == 0:
        if level == 0:
            return CARDINAL_BASIS[idx-1]
        else:
            return current_vector
    W = decomposition_vectors_about_x_axis[idx-1]
    
    # Get the rotation matrix
    R = rot_x_matrix(current_vector)
    X = (W * R).A[0]  # 3x3 Matrix * 1x3 Array ==> 1x3 Matrix ... grab the one and only 1-D vector from the 1-D matrix
    #  This next line shouldn't be necessary, but seems to be
    X = X / numpy.linalg.norm(X)
    if level > 1:
        for i in range(level-1):
            X = current_vector + X
            X = X / numpy.linalg.norm(X)  # normalize, not divide by 2.  Divide by 2 gives the middle point on the chord and not on the sphere.
    return X


# Compute arc-distance between two vectors
def distance(Vect, Wect):    
    c = numpy.dot(Vect, Wect)
    if 1.0 <= c:
        return 0
    if c <= -1.0 :
        return math.pi
    
    d = numpy.arccos(c)
    return d;

# Converts a single character in a spherical_geohash string to an angle.
# Called recursively to evaluate a spherical_geohash string
def nibble2vect(level, letter, current_vector=numpy.array([0.0,0.0,0.0])):
    idx = ord(letter) - ord('0')
    if level == 0:
        vect = CARDINAL_BASIS[idx-1]
    else:
        vect = decomposition_vector(current_vector, level, letter)
    return vect

# Heart of this geo-hashing code.  Iteratively finds the decomposed vectors that best 
# describe the objective vector.    
def hash(xyz, level, search_level=0, seed_hashes = []):
    objective = A(xyz)
    letters = ['0', '1', '2', '3', '4', '5', '6']    
    current_vector = A([0,0,0])
    search_dist = level_to_radians(search_level)
    hashes = [""]
    step_start = 0
    step_end = level
    if len(seed_hashes) > 0:
        hashes = seed_hashes
        step_start = len(seed_hashes)
        step_end = level - step_start + 1
    
    for step in range(step_start, step_end):
        letter_start = 1
        if step > 0:
            letter_start = 0
            
        def possible(letter):
            U = nibble2vect(step, letter, current_vector)  # use same function for forward and reverse encoding for consistent results
            dist = distance(objective, U)
            return (dist, letter, U)
            
        possibles = map(possible, letters[letter_start:])
        possibles.sort()
        
        # check to see if search_level criteria are matched by other options
        if search_level != 0 and step <= search_level:
            for tup in possibles[1:]:
                if tup[0] < search_dist + possibles[0][0]:
                    if step < search_level -1:
                        hashes = hashes + hash(xyz, search_level, search_level, [hashes[0] + tup[1]])
                    else:
                        hashes.append(hashes[0] + tup[1])
            
        # we will continue to drill into the best (minimal) path
        (min_dist, next_hash_letter, current_vector) = possibles[0]
        hashes[0] = hashes[0] + next_hash_letter
        
    return hashes

    
def vector(hash):
    current_vector=numpy.array([0.0,0.0,0.0])
    for i in range(len(hash)):
        letter = hash[i:i+1]
        current_vector = nibble2vect(i, letter, current_vector)
    return current_vector

def xyz2angles(xyz):
    lon_radians = numpy.arctan2(xyz[1], xyz[0])
    lat_radians = numpy.arcsin(xyz[2])
    return [lat_radians, lon_radians]

def angles2xyz(latlon_radians):
    xyz = [math.cos(latlon[0]) * math.cos(latlon[1]), math.cos(latlon[0]) * math.sin(latlon[1]), math.sin(latlon[0])]
    return xyz