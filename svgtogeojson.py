#!/usr/bin/python

import sys
import json,copy,re
from xml.etree import ElementTree as ET
import numpy as np
from more_itertools import peekable

np.cosd = lambda x: np.cos(x*np.pi/180)
np.sind = lambda x: np.sin(x*np.pi/180)

xscale = 0.01
yscale = 0.01

geodata = { "type": "FeatureCollection", "features": [] }
featuretemplate = {
    "type": "Feature",
    "properties": { "tags": { "name": "default room name" },
        "relations": [ { "reltags": { "height": "4", "level": "0", "type": "level" } } ],
        "meta": {}
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [[]]
    }
}

def transformPoint(pt):
    # Inkscape uses +y up coordinates internally
    # this doesn't invert the y-axis for now, but might at some point...
    return np.add(np.multiply(pt,[1*xscale,1*yscale]),[0,0]).tolist()

def matrixTransform(L,R):
    # L is given in SVG order, abcdef, zero-padded if 6 elements not given
    L += ([0]*(6-len(L)) if len(L) < 6 else [])
    L = np.vstack( [ np.reshape( L, (3,2) ).transpose(), [0,0,1] ] )
    return np.dot( L, R )

def getCoord(iterable):
    return float(iterable.next())

def main():
    ns="http://www.w3.org/2000/svg"
    if len(sys.argv) > 1 :
        try:
            xmltree = ET.parse(sys.argv[1])
        except IOError:
            print("Error, not a valid file")
            sys.exit(1)
        except:
            print("Unknown error")
            sys.exit(1)
    else:
        print("No SVG to parse specified!")
        print("Usage: python svgRectToGeoJSON.py file.svg")
        sys.exit(1)

    shapes = []
    shapes += xmltree.getroot().findall("./{%s}g/{%s}rect"%(ns,ns))
    shapes += xmltree.getroot().findall("./{%s}g/{%s}path"%(ns,ns))

    for s in shapes:
        shapeid = s.get('id')
        if ( s.tag == '{%s}rect'%ns ):
            x = float(s.get('x'))
            y = float(s.get('y'))
            w = float(s.get('width'))
            h = float(s.get('height'))
            pts = [ np.reshape(p+[1],(3,1)) for p in [ [x,y],[x+w,y],[x+w,y+h],[x,y+h],[x,y] ] ]

            transforms = re.findall("[a-zA-Z]+\([^\)]+\)",s.get('transform') or '')
            # reverse order because SVG transforms apply right-to-left
            transforms.reverse()
            mat = np.identity(3)
            for t in transforms:
                # TODO: factor to eliminate repeated calls to re.sub() and np.dot()
                if t.startswith("matrix"):
                    t = re.sub("[a-zA-Z]+\(([^\)]+)\)","\\1",t)
                    mat = matrixTransform( [ float(n) for n in re.split("[ ,]",t) ], mat )
                # TODO: translate, skewX, skewY transforms
                elif t.startswith("translate"):
                    pass
                elif t.startswith("skew"):
                    pass
                elif t.startswith("scale"):
                    t = re.sub("[a-zA-Z]+\(([^\)]+)\)","\\1",t)
                    n = re.split("[ ,]",t)
                    sx = float(n[0])
                    sy = float(n[1]) if len(n)>1 else sx # y scale is optional
                    mat = matrixTransform( [ sx,0,0,sy,0,0 ], mat )
                elif t.startswith("rotate"):
                    # TODO: rotate about a given point using translate() and this code
                    t = re.sub("[a-zA-Z]+\(([^\)]+)\)","\\1",t)
                    n = re.split("[ ,]",t)
                    a = float(n[0])
                    x = float(n[1]) if len(n)>1 else None
                    y = float(n[2]) if len(n)>1 else None
                    mat = matrixTransform( [ np.cosd(a), np.sind(a), -np.sind(a), np.cosd(a) ], mat )

            # this is gross
            pts = [ np.dot(mat,p)[0:2].transpose().tolist()[0] for p in pts ]
            geomObject(pts,name=shapeid)
        elif ( s.tag == '{%s}path'%ns ):
            pathdata = re.split("([a-zA-Z, ])",s.get('d'))
            # split ops and their arguments, discard whitespace and commas
            # peekable() is used instead of iter() so we can peek() at next value
            ops = peekable( filter( (lambda str: not str.isspace() and str not in ['',',']), pathdata))
            spot = [0,0]
            pts = []
            for o in ops:
                if( o.isalpha() ):
                    if ( o == 'Z' or o == 'z' ): # close path command
                        pts.append( pts[0] )
                        break
                    elif ( o == 'M' or o == 'm' ):
                        pts = []
                        while not ops.peek().isalpha():
                            if ( o == 'M' ):
                                spot = [getCoord(ops),getCoord(ops)]
                            elif ( o == 'm' ):
                                spot[0] += getCoord(ops)
                                spot[1] += getCoord(ops)
                            pts.append(spot)
                        print >> sys.stderr, "Path pts %s"%pts
                        geomObject(pts,name=shapeid)
#                    elif ( o == 'H' ): # horizontal line command
#                        spot[0] = getCoord(o)
#                    elif ( o == 'h' ):
#                        spot[0] += getCoord(o)
#
#                    elif ( o == 'V' ): # vertical line command
#                        spot[1] = getCoord(o)
#                    elif ( o == 'v' ):
#                        spot[1] += getCoord(o)
#
#                    elif ( o == 'L' ): # line command
#                        spot[0] = getCoord(o)
#                        spot[1] = getCoord(o)
#                    elif ( o == 'l' ):
#                        spot[0] += getCoord(o)
#                        spot[1] += getCoord(o)
#
#                    # the only non-drawing directives M and Z will skip this bit
#                    pts.append(spot)
                else:
                    print >> sys.stderr, "Unexpected <path> operation %s, ignoring..." % o
        else:
            print >> sys.stderr, "Unhandled tag %s encountered, skipping..." % s.tag

    print(json.dumps(geodata, indent=3))

def geomObject(pts,name="default room"):
    f = copy.deepcopy(featuretemplate)
    for pt in pts:
        f['geometry']['coordinates'][0].append( transformPoint(pt) )
    f['properties']['tags']['name'] = name
    geodata['features'].append(f)

if __name__ == "__main__":
    main()
