#!/usr/bin/env python3

# TODO: implement PERSPECTIVE_WH

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from PIL import Image
from PIL import ImageOps

import argparse
import io
import sys

from mascotcapsule import Figure
import sexpr

width, height = 240, 320
#width, height = 768, 1024

def render():
    pass

def draw():
    render()
    glutSwapBuffers()

def draw_figure_faces(figure):
    for face in figure.faces:
        if len(face) == 9:
            a, b, c, u1, v1, u2, v2, u3, v3 = face

            glBegin(GL_TRIANGLES)
            glTexCoord2d(u1, v1)
            glVertex3d(*figure.vertices[a])
            glTexCoord2d(u2, v2)
            glVertex3d(*figure.vertices[b])
            glTexCoord2d(u3, v3)
            glVertex3d(*figure.vertices[c])
            glEnd()

            #print('triangle', figure.vertices[a], figure.vertices[b], figure.vertices[c],
            #        (u1, v1), (u2, v2), (u3, v3))
        else:
            a, b, c, d, u1, v1, u2, v2, u3, v3, u4, v4 = face

            glBegin(GL_QUADS)
            glTexCoord2d(u1, v1)
            glVertex3d(*figure.vertices[a])
            glTexCoord2d(u2, v2)
            glVertex3d(*figure.vertices[b])
            glTexCoord2d(u4, v4)
            glVertex3d(*figure.vertices[d])
            glTexCoord2d(u3, v3)
            glVertex3d(*figure.vertices[c])
            glEnd()

def get_figure_by_ref(figures, ref):
    if ref not in figures:
        with open(ref + '.mbac', 'rb') as f:
            figures[ref] = Figure.fromfile(f)

    return figures[ref]

def get_texture_by_ref(textures, ref):
    if ref not in textures:
        img = Image.open(ref + '.bmp')

        textures[ref] = texture_from_image(img)        

    return textures[ref]

def inject_figure(figures, ref, bytes):
    figures[ref] = Figure.fromfile(io.BytesIO(bytes))

def inject_texture(textures, ref, bytes):
    img = Image.open(io.BytesIO(bytes))

    textures[ref] = texture_from_image(img)

def texture_from_image(img):
    img = img.convert('RGB')
    img_data = list(img.getdata())

    id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, id)

    interp = GL_NEAREST     # linear looks like shit!

    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, interp)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, interp)
    glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.size[0], img.size[1], 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)

    return dict(id=id, w=img.size[0], h=img.size[1])

def main(filename):
    with open(filename, 'rt') as f:
        log = sexpr.load(f)
        #print(log)

    assert log[0] == 'mascotcapsule-command-log'

    glutInit(sys.argv)

    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(width, height)
    glutCreateWindow(b"OpenGL Offscreen")
    glutHideWindow()

    glViewport(0, 0, width, height)
    glClearColor(1.0, 0.0, 1.0, 1.0)

    # MCv3 doesn't have a proper depth buffer, it just does a Z-sort within each drawn model
    # we emulate this by clearing the depth buffer between every draw
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)

    figures = {}
    textures = {}

    def bind_texture(ref):
        texture = get_texture_by_ref(textures, figure['texture'])

        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture['id'])

        glMatrixMode(GL_TEXTURE)
        glLoadIdentity()
        glTranslate(0, 1, 0)
        glScale(1 / texture['w'], 1 / texture['h'], 1)

    def setup_layout(x, y, layout):
        # TODO: handle x, y
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        #glTranslate(0, 0, -1)

        matrix = [float(x) / 4096 for x in layout['affineTrans']]

        # order here is column-major! unlike mcv3!
        glMultMatrixd([matrix[0], matrix[4], matrix[8], 0,
                       matrix[1], matrix[5], matrix[9], 0,
                       matrix[2], matrix[6], matrix[10], 0,
                       matrix[3], matrix[7], matrix[11], 1
                       ])
        #

        glScale(1 / 4096, 1 / 4096, 1 / 4096)

        assert layout['projection'] == 'PERSPECTIVE_FOV'
        zNear, zFar, fov = [float(x) for x in layout['perspective']]

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(fov * (360 / 4096), width / height, zNear / 4096, zFar / 4096)

    frames = []

    for entry in log[1:]:
        if entry[0] == 'frame':
            frames.append(entry)
        elif entry[0] == 'data':
            for data_entry in entry[1:]:
                if data_entry[0] == 'figure':
                    inject_figure(figures, data_entry[1], bytes.fromhex(data_entry[2]))
                elif data_entry[0] == 'texture':
                    inject_texture(textures, data_entry[1], bytes.fromhex(data_entry[2]))
                else:
                    print('warning: skipping data type', entry[0])
        else:
            print('warning: skipping', entry[0])

    for frame_no, frame in enumerate(frames):
        glClear(GL_COLOR_BUFFER_BIT)
        render()

        for command in frame[1:]:
            if command[0] in ('drawFigure', 'renderFigure'):
                # TODO: handle effect3D
                args = sexpr.as_dict(command[1:])

                figure = sexpr.as_dict(args['figure'][1:])
                fig = get_figure_by_ref(figures, args['figure'][0])

                bind_texture(figure['texture'])
                setup_layout(int(args['x']), int(args['y']), sexpr.as_dict(args['layout']))

                #gluOrtho2D(-1.0, 1.0, -1.0, 1.0)

                glClear(GL_DEPTH_BUFFER_BIT)
                draw_figure_faces(fig)

            elif command[0] in ('renderPrimitives',):
                args = sexpr.as_dict(command[1:])

                bind_texture(args['texture'])
                setup_layout(int(args['x']), int(args['y']), sexpr.as_dict(args['layout']))

                # command numPrimitives, vertexCoords, normals, textureCoords, colors
                command_tokens = args['command'].split('|')

                if command_tokens[0] == 'PRIMITVE_QUADS':
                    glClear(GL_DEPTH_BUFFER_BIT)

                    glBegin(GL_QUADS)
                    for i in range(int(args['numPrimitives'])):
                        s, t = [float(x) for x in args['textureCoords'][i*2:i*2+2]]
                        glTexCoord2d(s, t)
                        x, y, z = [float(x) for x in args['vertexCoords'][i*3:i*3+3]]
                        glVertex3d(x, y, z)
                    glEnd()
                else:
                    # eg PRIMITVE_POINT_SPRITES
                    print('warning: skipping', command_tokens[0])
            else:
                #raise Exception(f'Unknown command "{command[0]}"')
                pass

        glFlush()

        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
        image = Image.frombytes("RGBA", (width, height), data)
        image = ImageOps.flip(image) # in my case image is flipped top-bottom for some reason
        image.save(f'render/{frame_no:03d}.png')

        glutSwapBuffers()

        #glutDisplayFunc(draw)
        #glutMainLoop()

parser = argparse.ArgumentParser()
parser.add_argument('logfile')

args = parser.parse_args()

main(args.logfile)
