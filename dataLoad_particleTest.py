import numpy as np
import os
import sys
import struct
import time
import random

import progressbar

maxParticlesPerGrid = 200
overrideGrid = True
overrideGridSize = 48

# np.set_printoptions(suppress=True)

def packGridHash(content, x, y, z):

    x = x % content['gridCountX']
    y = y % content['gridCountY']
    z = z % content['gridCountZ']

    return y * content['gridCountZ'] * content['gridCountX'] + x * content['gridCountZ'] + z

def unpackGridHash(content, hash):

    gridX = hash % (content['gridCountZ'] * content['gridCountX']) // content['gridCountZ']
    gridY = hash // (content['gridCountZ'] * content['gridCountX'])
    gridZ = hash % content['gridCountZ']

    return (gridX, gridY, gridZ)

def get_fileNames(main_dir):
    
    files = []

    for filename in os.listdir(main_dir):
        if filename.split('.')[-1] == 'mdset':
            files.append(os.path.join(main_dir, filename))
    
    return files

def fileCount(path):
    return len(get_fileNames(path))

def read_file_header(filename):

    file = open(filename, 'rb')
    file_content = {}

    print('Reading file ' + filename)

    # Read file header
    file_content['gridCountX'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['gridCountY'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['gridCountZ'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    file_content['gridCount'] = file_content['gridCountX'] * file_content['gridCountY'] * file_content['gridCountZ']

    file_content['gridSize'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    tmp = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    if tmp == 0:
        file_content['gravity'] = False
    else:
        file_content['gravity'] = True

    tmp = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    if tmp == 0:
        file_content['boundary'] = False
    else:
        file_content['boundary'] = True

    file_content['stepCount'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    # Start a progress bar
    bar = progressbar.ProgressBar(maxval = file_content['stepCount'], widgets = [progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()

    # create data buffer

    # Data format: 6 - [locationX, locationY, locationZ, velocityX, velocityY, velocityZ]
    # file_content['data'] = np.zeros((file_content['stepCount'], file_content['gridCount'], maxParticlesPerGrid, 6))

    file_content['particleCount'] = np.zeros((file_content['stepCount'], file_content['gridCount']), dtype = np.int32)
    file_content['maxParticles'] = 0
    file_content['particleCountHistogram'] = np.zeros((maxParticlesPerGrid,), dtype = np.int32)

    # Read file content
    for step in range(file_content['stepCount']):

        current_step = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

        for grid in range(file_content['gridCount']):

            pCount = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
            file_content['particleCountHistogram'][pCount] += 1

            # Count max particles in a single grid
            if file_content['maxParticles'] < pCount:
                file_content['maxParticles'] = pCount
            
            file.read(24 * pCount)

        bar.update(current_step)
    
    bar.finish()

    return file_content

def read_file_override(filename, vM = 1.0):

    file = open(filename, 'rb')
    file_content = {}

    print('Reading file ' + filename)

    # Read file header
    file_content['gridCountX'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['gridCountY'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['gridCountZ'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['originalGridCount'] = file_content['gridCountX'] * file_content['gridCountY'] * file_content['gridCountZ']

    file_content['gridSize'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    file_content['worldSize'] = file_content['gridCountX'] * file_content['gridSize']
    assert file_content['worldSize'] % overrideGridSize == 0 # perfect grid

    tmp = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    if tmp == 0:
        file_content['gravity'] = False
    else:
        file_content['gravity'] = True

    tmp = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    if tmp == 0:
        file_content['boundary'] = False
    else:
        file_content['boundary'] = True

    file_content['stepCount'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    # Override part
    file_content['gridSize'] = overrideGridSize
    file_content['gridCountX'] = file_content['worldSize'] // file_content['gridSize']
    file_content['gridCountY'] = file_content['worldSize'] // file_content['gridSize']
    file_content['gridCountZ'] = file_content['worldSize'] // file_content['gridSize']

    file_content['gridCount'] = file_content['gridCountX'] * file_content['gridCountY'] * file_content['gridCountZ']
    print("overrided grid count: %d" % file_content['gridCount'])

    # Start a progress bar
    bar = progressbar.ProgressBar(maxval = file_content['stepCount'], widgets = [progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()

    # create data buffer

    # Data format: 6 - [locationX, locationY, locationZ, velocityX, velocityY, velocityZ]
    file_content['data'] = np.zeros((file_content['stepCount'], file_content['gridCount'], maxParticlesPerGrid, 6))

    file_content['particleCount'] = np.zeros((file_content['stepCount'], file_content['gridCount']), dtype = np.int32)
    file_content['maxParticles'] = 0
    pCount = np.zeros((1,), dtype = np.int32)

    # Read file content
    for step in range(file_content['stepCount']):

        current_step = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

        for grid in range(file_content['originalGridCount']):

            pCount[0] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
            # file_content['particleCount'][current_step, grid] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
            # print(pCount)

            byte_data = file.read(24 * pCount[0])

            # Read particles
            for particle in range(pCount[0]):

                (pX, pY, pZ, vX, vY, vZ) = struct.unpack('6f', byte_data[particle * 24 : particle * 24 + 24])
                pX = (pX + file_content['worldSize'] / 2)
                pZ = (pZ + file_content['worldSize'] / 2)
                gX = int(pX // file_content['gridSize'])
                gY = int(pY // file_content['gridSize'])
                gZ = int(pZ // file_content['gridSize'])

                # grid it belongs to
                true_grid = packGridHash(file_content, gX, gY, gZ)
                # print(true_grid)

                gridPosX = gX * file_content['gridSize']
                gridPosY = gY * file_content['gridSize']
                gridPosZ = gZ * file_content['gridSize']

                # TODO: Data normalization
                curIdx = file_content['particleCount'][current_step, true_grid]
                if curIdx >= maxParticlesPerGrid:
                    curIdx = maxParticlesPerGrid - 1

                file_content['data'][current_step, true_grid, curIdx, 0] = pX - gridPosX - file_content['gridSize'] / 2
                file_content['data'][current_step, true_grid, curIdx, 1] = pY - gridPosY - file_content['gridSize'] / 2
                file_content['data'][current_step, true_grid, curIdx, 2] = pZ - gridPosZ - file_content['gridSize'] / 2

                file_content['data'][current_step, true_grid, curIdx, 3] = vX * vM
                file_content['data'][current_step, true_grid, curIdx, 4] = vY * vM
                file_content['data'][current_step, true_grid, curIdx, 5] = vZ * vM

                file_content['particleCount'][current_step, true_grid] += 1

                # np.set_printoptions(edgeitems = 16, suppress = True, precision = 2)
                # print("#%5d in g%6d(%+2d, %+2d, %+2d): %+3.2f %+3.2f %+3.2f -> %s" % (file_content['particleCount'][current_step, true_grid], true_grid, gX, gY, gZ, pX, pY, pZ, str(file_content['data'][current_step, true_grid, curIdx, :])))

                if(file_content['particleCount'][current_step, true_grid] > file_content['maxParticles']):
                    file_content['maxParticles'] = file_content['particleCount'][current_step, true_grid]

        bar.update(current_step)
    
    bar.finish()

    if file_content['maxParticles'] > maxParticlesPerGrid:
        print("Overflow - %d particles in a grid !" % (file_content['maxParticles']))

    return file_content

def read_file(filename, vM = 1.0):

    file = open(filename, 'rb')
    file_content = {}

    print('Reading file ' + filename)

    # Read file header
    file_content['gridCountX'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['gridCountY'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['gridCountZ'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    file_content['gridCount'] = file_content['gridCountX'] * file_content['gridCountY'] * file_content['gridCountZ']

    file_content['gridSize'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    tmp = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    if tmp == 0:
        file_content['gravity'] = False
    else:
        file_content['gravity'] = True

    tmp = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    if tmp == 0:
        file_content['boundary'] = False
    else:
        file_content['boundary'] = True

    file_content['stepCount'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    # Start a progress bar
    bar = progressbar.ProgressBar(maxval = file_content['stepCount'], widgets = [progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()

    # create data buffer

    # Data format: 6 - [locationX, locationY, locationZ, velocityX, velocityY, velocityZ]
    file_content['data'] = np.zeros((file_content['stepCount'], file_content['gridCount'], maxParticlesPerGrid, 6))

    file_content['particleCount'] = np.zeros((file_content['stepCount'], file_content['gridCount']), dtype = np.int32)
    file_content['maxParticles'] = 0

    # Read file content
    for step in range(file_content['stepCount']):

        current_step = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

        for grid in range(file_content['gridCount']):

            file_content['particleCount'][current_step, grid] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

            # Compute grid position
            # By default, X & Z centered at zero (-x/2 - x/2), Y started from zero (0 - y)
            # UINT hashVal = (yCube * dset_CUBE_COUNTz_1D * dset_CUBE_COUNTx_1D) + (zCube + xCube * dset_CUBE_COUNTz_1D);
            gridPosX = grid % (file_content['gridCountZ'] * file_content['gridCountX']) // file_content['gridCountZ'] * file_content['gridSize'] - (file_content['gridCountX'] // 2 * file_content['gridSize'])
            gridPosY = grid // (file_content['gridCountZ'] * file_content['gridCountX']) * file_content['gridSize']
            gridPosZ = grid % file_content['gridCountZ'] * file_content['gridSize'] - (file_content['gridCountZ'] // 2 * file_content['gridSize'])

            # Count max particles in a single grid
            if file_content['maxParticles'] < file_content['particleCount'][current_step, grid]:
                file_content['maxParticles'] = file_content['particleCount'][current_step, grid]
            
            byte_data = file.read(24 * file_content['particleCount'][current_step, grid])

            # Read particles
            for particle in range(file_content['particleCount'][current_step, grid]):

                # Position
                (file_content['data'][current_step, grid, particle, 0], file_content['data'][current_step, grid, particle, 1],\
                 file_content['data'][current_step, grid, particle, 2], file_content['data'][current_step, grid, particle, 3],\
                 file_content['data'][current_step, grid, particle, 4], file_content['data'][current_step, grid, particle, 5]) =\
                struct.unpack('6f', byte_data[particle * 24 : particle * 24 + 24])

                # TODO: Data normalization
                file_content['data'][current_step, grid, particle, 0] -= gridPosX + file_content['gridSize'] / 2
                file_content['data'][current_step, grid, particle, 1] -= gridPosY + file_content['gridSize'] / 2
                file_content['data'][current_step, grid, particle, 2] -= gridPosZ + file_content['gridSize'] / 2

                ### FIXME: Replace position as noise
                # file_content['data'][current_step, grid, particle, 0] = np.random.normal(scale = 1.0)
                # file_content['data'][current_step, grid, particle, 1] = np.random.normal(scale = 1.0)
                # file_content['data'][current_step, grid, particle, 2] = np.random.normal(scale = 1.0)

                # file_content['data'][current_step, grid, particle, 0] = 0
                # file_content['data'][current_step, grid, particle, 1] = 0
                # file_content['data'][current_step, grid, particle, 2] = 0
                ### FIXME

                file_content['data'][current_step, grid, particle, 3] *= vM
                file_content['data'][current_step, grid, particle, 4] *= vM
                file_content['data'][current_step, grid, particle, 5] *= vM

        bar.update(current_step)
    
    bar.finish()

    return file_content

def read_file_predict(filename, start_step, vM = 1.0):

    file = open(filename, 'rb')
    file_content = {}

    print('Reading file ' + filename)

    # Read file header
    file_content['gridCountX'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['gridCountY'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    file_content['gridCountZ'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    print(file_content)

    file_content['gridCount'] = file_content['gridCountX'] * file_content['gridCountY'] * file_content['gridCountZ']

    file_content['gridSize'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    tmp = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    if tmp == 0:
        file_content['gravity'] = False
    else:
        file_content['gravity'] = True

    tmp = int.from_bytes(file.read(4), byteorder = 'little', signed = False)
    if tmp == 0:
        file_content['boundary'] = False
    else:
        file_content['boundary'] = True

    file_content['stepCount'] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

    # Start a progress bar
    bar = progressbar.ProgressBar(maxval = file_content['stepCount'], widgets = [progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()

    # create data buffer

    # Data format: 6 - [locationX, locationY, locationZ, velocityX, velocityY, velocityZ]
    file_content['data'] = np.zeros((file_content['stepCount'], file_content['gridCount'], maxParticlesPerGrid, 6))

    file_content['particleCount'] = np.zeros((file_content['stepCount'], file_content['gridCount']), dtype = np.int32)
    file_content['maxParticles'] = 0

    # Read file content
    for step in range(file_content['stepCount']):

        current_step = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

        for grid in range(file_content['gridCount']):

            file_content['particleCount'][current_step, grid] = int.from_bytes(file.read(4), byteorder = 'little', signed = False)

            # Compute grid position
            # By default, X & Z centered at zero (-x/2 - x/2), Y started from zero (0 - y)
            # UINT hashVal = (yCube * dset_CUBE_COUNTz_1D * dset_CUBE_COUNTx_1D) + (zCube + xCube * dset_CUBE_COUNTz_1D);
            gridPosX = grid % (file_content['gridCountZ'] * file_content['gridCountX']) // file_content['gridCountZ'] * file_content['gridSize'] - (file_content['gridCountX'] // 2 * file_content['gridSize'])
            gridPosY = grid // (file_content['gridCountZ'] * file_content['gridCountX']) * file_content['gridSize']
            gridPosZ = grid % file_content['gridCountZ'] * file_content['gridSize'] - (file_content['gridCountZ'] // 2 * file_content['gridSize'])

            # Count max particles in a single grid
            if file_content['maxParticles'] < file_content['particleCount'][current_step, grid]:
                file_content['maxParticles'] = file_content['particleCount'][current_step, grid]
            
            # Read only first step
            byte_data = file.read(24 * file_content['particleCount'][current_step, grid])

            # Read particles
            for particle in range(file_content['particleCount'][current_step, grid]):

                if current_step < start_step:
                    # Position
                    (file_content['data'][current_step, grid, particle, 0], file_content['data'][current_step, grid, particle, 1],\
                     file_content['data'][current_step, grid, particle, 2], file_content['data'][current_step, grid, particle, 3],\
                     file_content['data'][current_step, grid, particle, 4], file_content['data'][current_step, grid, particle, 5]) =\
                    struct.unpack('6f', byte_data[particle * 24 : particle * 24 + 24])

                    # TODO: Data normalization
                    file_content['data'][current_step, grid, particle, 0] -= gridPosX + file_content['gridSize'] / 2
                    file_content['data'][current_step, grid, particle, 1] -= gridPosY + file_content['gridSize'] / 2
                    file_content['data'][current_step, grid, particle, 2] -= gridPosZ + file_content['gridSize'] / 2

                    file_content['data'][current_step, grid, particle, 3] *= vM
                    file_content['data'][current_step, grid, particle, 4] *= vM
                    file_content['data'][current_step, grid, particle, 5] *= vM

        bar.update(current_step)
    
    bar.finish()

    return file_content

def gen_batch(content, batch_size, is_Train = True):
    
    if is_Train == True:
        start = 0.0
        # end = 0.9
        end = 1.0
    else:
        return
        # start = 0.9
        start = 1.0
        end = 1.0
    
    batch_X = np.zeros((batch_size, maxParticlesPerGrid, 7))
    batch_X_size = np.zeros((batch_size))
    batch_idx = 0
    avgCard = 0

    # shuffle the steps
    steps = list(range(content['stepCount']))
    grids = list(range(content['gridCount']))
    random.shuffle(steps)
    # steps = steps[0:(len(steps) // 4)]

    # in order to get validation set "pure" from training set, shuffling with a fixed order
    random.Random(8246).shuffle(grids)

    for step in steps:
        for grid_idx in range(int(start * content['gridCount']), int(end * content['gridCount'])):

            grid = grids[grid_idx]

            # Skip empty grids
            if content['particleCount'][step, grid] <= 0:
                continue

            batch_X[batch_idx, :, :] = 0
            batch_X_size[batch_idx] = 0

            (gridX, gridY, gridZ) = unpackGridHash(content, grid)

            # Fill training data
            batch_X[batch_idx, :, 0:3] = content['data'][step, packGridHash(content, gridX, gridY, gridZ), :, 0:3]
            batch_X[batch_idx, :, 3:6] = content['data'][step, packGridHash(content, gridX, gridY, gridZ), :, 3:6]
            batch_X[batch_idx, 0:content['particleCount'][step, packGridHash(content, gridX, gridY, gridZ)], 6] = 1

            batch_X_size[batch_idx] = max(0, min(maxParticlesPerGrid, content['particleCount'][step, grid]))

            avgCard += batch_X_size[batch_idx]

            # Count batch
            batch_idx += 1
            if batch_idx >= batch_size:
                batch_idx = 0

                print("Avg card = %6.2f" % (avgCard / batch_size), end = ' ')
                avgCard = 0

                # Calculate mean value
                # print(np.mean(batch_X[:, 13, :, 0:3], axis = (0, 1)))

                # np.set_printoptions(edgeitems = 16, suppress = True, precision = 2)
                # print(batch_X)
                # input('Press anykey...')

                yield batch_X, batch_X_size
                
def gen_batch_predict(content, batch_size, currentStep, step_count):
    
    batch_X = np.zeros((batch_size, 27, maxParticlesPerGrid, 6))
    batch_Y = np.zeros((batch_size, maxParticlesPerGrid, 6))
    batch_Y_size = np.zeros((batch_size))
    batch_idx = 0
    
    for grid in range(int(content['gridCount'])):

        (gridX, gridY, gridZ) = unpackGridHash(content, grid)

        # Fill training data from 3x3x3 neighboors
        for xx in range(-1, 2):
            for yy in range(-1, 2):
                for zz in range(-1, 2):
                    offsetHash = (xx + 1) * 3 * 3 + (yy + 1) * 3 + (zz + 1)
                    batch_X[batch_idx, offsetHash, :, 0:3] = content['data'][currentStep, packGridHash(content, gridX + xx, gridY + yy, gridZ + zz), :, 0:3]
                    batch_X[batch_idx, offsetHash, :, 3:6] = np.asarray([xx, yy, zz])

        batch_Y[batch_idx, :, 0:3] = content['data'][currentStep + step_count, grid, :, 0:3]
        batch_Y_size[batch_idx] = content['particleCount'][currentStep + step_count, grid]

        # Count batch
        batch_idx += 1
        if batch_idx >= batch_size:
            batch_idx = 0
            yield batch_X, batch_Y, batch_Y_size
    
    batch_idx = 0
    yield batch_X, batch_Y, batch_Y_size

def gen_epochs(n_epochs, path, batch_size, vM):

    files = get_fileNames(path)
    # for i in range(len(files)):
    #     read_file(files[i])

    for i in range(n_epochs):
    # for i in range(n_epochs * len(files)):
        if overrideGrid:
            print("Reading in override mode...")
            content = read_file_override(files[i % len(files)], vM)
        else:
            content = read_file(files[i % len(files)], vM)
        # content = read_file(files[0], step_count * vM)
        yield gen_batch(content, batch_size, is_Train = True), gen_batch(content, batch_size, is_Train = False)

def gen_epochs_predict(path, start_step, batch_size, step_count, vM):

    content = read_file_predict(path, start_step, step_count * vM)

    i = start_step - 1
    while i < (content['stepCount'] - step_count):
        yield gen_batch_predict(content, batch_size, i, step_count), content
        i += step_count

def write_content(content, step, gridHash, particleArray, particleCount):
    if(gridHash < content['gridCount']):
        content['data'][step, gridHash, 1:particleCount+1, 0:6] = particleArray[0:particleCount, 0:6]

def save_file(content, filename, vM):
    file = open(filename, 'wb')

    print('Writing file ' + filename)

    # File header
    file.write(content['gridCountX'].to_bytes(4, byteorder = 'little', signed = False))
    file.write(content['gridCountY'].to_bytes(4, byteorder = 'little', signed = False))
    file.write(content['gridCountZ'].to_bytes(4, byteorder = 'little', signed = False))

    file.write(content['gridSize'].to_bytes(4, byteorder = 'little', signed = False))

    if content['gravity'] == True:
        file.write((1).to_bytes(4, byteorder = 'little', signed = False))
    else:
        file.write((0).to_bytes(4, byteorder = 'little', signed = False))

    if content['boundary'] == True:
        file.write((1).to_bytes(4, byteorder = 'little', signed = False))
    else:
        file.write((0).to_bytes(4, byteorder = 'little', signed = False))

    file.write(content['stepCount'].to_bytes(4, byteorder = 'little', signed = False))

    # Start a progress bar
    bar = progressbar.ProgressBar(maxval = content['stepCount'], widgets = [progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
    bar.start()

    for i in range(content['stepCount']):

        # Current step
        file.write(i.to_bytes(4, byteorder = 'little', signed = False))

        # Grids
        for grid in range(content['gridCount']):
            
            file.write(content['particleCount'][i, grid].tobytes())

            gridPosX = grid % (content['gridCountZ'] * content['gridCountX']) // content['gridCountZ'] * content['gridSize'] - (content['gridCountX'] // 2 * content['gridSize'])
            gridPosY = grid // (content['gridCountZ'] * content['gridCountX']) * content['gridSize']
            gridPosZ = grid % content['gridCountZ'] * content['gridSize'] - (content['gridCountZ'] // 2 * content['gridSize'])

            for particle in range(content['particleCount'][i, grid]):
                
                x = content['data'][i, grid, particle, 0] + gridPosX + (content['gridSize'] / 2)
                y = content['data'][i, grid, particle, 1] + gridPosY + (content['gridSize'] / 2)
                z = content['data'][i, grid, particle, 2] + gridPosZ + (content['gridSize'] / 2)

                vX = content['data'][i, grid, particle, 3] / vM
                vY = content['data'][i, grid, particle, 4] / vM
                vZ = content['data'][i, grid, particle, 5] / vM

                file.write(struct.pack('6f', x, y, z, vX, vY, vZ))
            
        bar.update(i)
    
    bar.finish()

    return
