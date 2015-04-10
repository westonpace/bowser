'''
Created on Mar 29, 2015

@author: Pace
'''
import sys
from bowser.app import Bowser

def main():
    if len(sys.argv) != 2:
        print("Usage: bowser [input-ram-file]")
        sys.exit(-1)
    bowser = Bowser()
    bowser.start(sys.argv[1])
    bowser.join()
    

if __name__ == '__main__':
    main()
