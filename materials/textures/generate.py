import OpenImageIO
import numpy
import random
import math

channels = [
    ("base_color",3),
    ("coat_color",3),
    ("metalness",1),
    ("sheen_color",3),
    ("specular",1),
    ("specular_color",3),
]
def pattern(w,h,x,y):
    xr = x
    yr = y
    xi = int(x/100.0)*100
    yi = int(y/100.0)*100
    xd = (x-xi)
    yd = (y-yi)
    v = math.sqrt(xd*xd+yd*yd)
    xii = (1+int(x/100.0))*100
    yii = (1+int(y/100.0))*100
    random.seed(yi*w+xi)
    xdd = (xii-xi)*random.random()
    ydd = (yii-yi)*random.random()
    r = random.random()
    g = random.random()
    b = random.random()
    vv = math.sqrt(xdd*xdd+ydd*ydd)
    return v/vv, r, g, b

width = 640
height = 640

base_color = numpy.zeros((height, width, 4), dtype=numpy.float32)
metalness = numpy.zeros((height, width, 1), dtype=numpy.float32)

random.seed(123)
for y in range(height):
    for x in range(width):
        n,r,g,b = pattern(width,height,x,y)
        metalness[y][x][0] = n
        base_color[y][x][0] = r
        base_color[y][x][1] = g
        base_color[y][x][2] = b
        base_color[y][x][3] = 1.0


out = OpenImageIO.ImageOutput.create("base_color.exr")
spec = OpenImageIO.ImageSpec(width, height, 4, 'float32')
out.open("base_color.exr", spec)
out.write_image(base_color)
out.close()

out = OpenImageIO.ImageOutput.create("metalness.exr")
spec = OpenImageIO.ImageSpec(width, height, 1, 'float32')
out.open("metalness.exr", spec)
out.write_image(metalness)
out.close()
