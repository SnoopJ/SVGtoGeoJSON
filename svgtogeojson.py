#!/usr/bin/python

import sys
import json
import copy
from xml.etree import ElementTree as ET
import numpy as np

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
        "coordinates": []
    }
}

def transformPoint(pt):
    return np.add(np.multiply(pt,[1*xscale,1*yscale]),[0,0]).tolist()

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
        roomid = s.get('id')
        if ( s.tag == '{%s}rect'%ns ): 
            x = float(s.get('x'))
            y = float(s.get('y'))
            w = float(s.get('width'))
            h = float(s.get('height'))
            if ( s.get('transform') ):
                mat = []
                pts = []
                for n in s.get('transform').replace('matrix(','').replace(')','').split(','):
                    mat.append( float(n) )
                m = np.vstack([np.resize(mat,(3,2)).transpose(), [0,0,1]])

                pts.append( transformPoint(np.dot(m,[x,y,1])[0:2]) )
                pts.append( transformPoint(np.dot(m,[x+w,y,1])[0:2]) )
                pts.append( transformPoint(np.dot(m,[x+w,y+h,1])[0:2]) )
                pts.append( transformPoint(np.dot(m,[x,y+h,1])[0:2]) )
                pts.append( pts[0] )
                geomObject(pts,name=roomid)
            else:
                rectObject(x,y,w,h,name=roomid)
        # TODO: paths

    print(json.dumps(geodata, indent=3))
         
def rectObject(x,y,w,h,name="default room"):
    geomObject(pts=[
        transformPoint([x,y]),
        transformPoint([x+w,y]), 
        transformPoint([x+w,y+h]), 
        transformPoint([x,y+h]), 
        transformPoint([x,y])
    ],name=name)

def geomObject(pts,name="default room"):
    f = copy.deepcopy(featuretemplate)
    f['geometry']['coordinates'] = [ pts ]
    f['properties']['tags']['name'] = name

    geodata['features'].append(f)

if __name__ == "__main__":
    main()

