import struct
import base64
import traceback
import json

#Create a list of translations for Cayenne types...
cayennetypes = {}
cayennetypes[0] = {
    "size": 1,
    "desc": "Digital In",
    "mult": 1,
    "format": "B"
}
cayennetypes[1] = {
    "size": 1,
    "desc": "Digital Out",
    "mult": 1,
    "format": "B"
}
cayennetypes[2] = {
    "size": 2,
    "desc": "Analog In",
    "mult": 0.01,
    "format": ">h"
}
cayennetypes[3] = {
    "size": 3,
    "desc": "Analog Out",
    "mult": 0.01,
    "format": ">h"
}
cayennetypes[101] = {
    "size": 2,
    "desc": "Brightness",
    "mult": 1,
    "format": ">h"
}
cayennetypes[102] = {
    "size": 1,
    "desc": "Presence",
    "mult": 1,
    "format": "B"
}
cayennetypes[103] = {
    "size": 2,
    "desc": "Temperature",
    "mult": 0.1,
    "format": ">h"
}
cayennetypes[104] = {
    "size": 1,
    "desc": "Humidity",
    "mult": 0.5,
    "format": "B"
}
cayennetypes[113] = {
    "size": [2,2,2],
    "desc": ["AccX","AccY","AccZ"],
    "mult": [0.001,0.001,0.001],
    "format": [">h",">h",">h"]
}
cayennetypes[115] = {
    "size": 2,
    "desc": "Barometer",
    "mult": 0.1,
    "format": ">h"
}
cayennetypes[134] = {
    "size": [2,2,2],
    "desc": ["GyroX","GyroY","GyroZ"],
    "mult": [0.01,0.01,0.01],
    "format": [">h",">h",">h"]
}
cayennetypes[136] = {
    "size": [4,4,2],    
    "mult": [0.0001,0.0001,0.01],
    "format": [">f",">f",">h"],
    "desc": ["Lat","Lon","Alt"]
}

#This represents a single math operation to be performed on an input
class PatternOp:
    def __init__(self):
        self.func = None
        self.value = 0

    def __repr__(self):
        return str(self.func) + " " + str(self.value)

#This represents a single, possible value match in the LORA pattern - including name, size and format.
class PatternMatch:
    def __init__(self,name,fmt,ops):
        self.name = name
        self.format = fmt
        if fmt[0] == 'S':
            self.size = int(fmt[1:])
            self.format = "S"
        else:
            self.size = struct.calcsize(fmt)
        self.ops = None

        if len(ops) > 0:
            op = None
            val = ""
            current = None
            self.ops = []            
            for x in range(0,len(ops)):
                c = ops[x]
                if c == "*" or c == "-" or c == "/" or c == "+" or c == "R":
                    if current is not None:
                        current.value = float(val)                        
                        self.ops.append(current)
                    current = PatternOp()
                    current.func = c
                    val = ""
                else:
                    val = val + str(c)

            if current is not None:                   
                current.value = float(val)                
                self.ops.append(current)

    #Perform any math transformations required.
    def Transform(self,val):
        if self.ops is not None:            
            val = float(val)
            for op in self.ops:                
                if op.func == "*":
                    val *= op.value                    
                if op.func == "+":
                    val += op.value
                if op.func == "-":
                    val -= op.value
                if op.func == "/":
                    val /= op.value                
                if op.func == "R":
                    val = round(val,int(op.value))

            return val
        else:
            return val

#Represents a single pattern that we can match LORA messages against.
class Pattern:
    def __init__(self,elements):
        x = 0
        groupopen = None
        self.patternparts = []
        self.cayenne = False

        if elements == "cayenne":
            self.cayenne = True
            return

        while x < len(elements):
            if elements[x] == '[':
                groupopen = x+1
            if elements[x] == ']':
                value = elements[groupopen:x]
                
                vset = []
                allvalues = value.split("|")                
                for q in range(0,len(allvalues)):
                    if allvalues[q][0] == "x":
                        vset.append(int(allvalues[q][1:],base=16))
                    else:
                        vset.append(int(allvalues[q]))

                self.patternparts.append(["=",vset])
                groupopen = None

            if elements[x] == '(':
                groupopen = x+1
            if elements[x] == ')':
                value = elements[groupopen:x].split(':')
            
                if len(value) == 2:
                    self.patternparts.append(PatternMatch(value[0],value[1],""))
                else:
                    self.patternparts.append(PatternMatch(value[0],value[1],value[2]))
                groupopen = None

            if elements[x] == '{':
                groupopen = x+1
            if elements[x] == '}':
                value = elements[groupopen:x].split(',')                
                if value[0] != "" and value[0][0] == '!':
                    value[0] = value[0][1:]
                    self.patternparts.append(["S",value])
                else:
                    self.patternparts.append(["B",value])
                
                groupopen = None

            if groupopen is None:
                if elements[x] == ".":
                    self.patternparts.append(["*",False])
            x += 1        

    #For cayenne messages, find new names when there are multiple sensors of the same type.
    def GetFreeName(self,name,dic):
        if name not in dic:
            return name
        
        st = 2
        newname = name + "2"
        while newname in dic:
            st += 1
            newname = name + str(st)

        return newname

    #Extract binary cayenne-format data into a dictionary
    def ExtractCayenne(self,buffer):
        global cayennetypes
        resp = {}
        q = 0
        while q < len(buffer):
            ch = buffer[q]
            typ = buffer[q+1]            

            q += 2

            if typ in cayennetypes:
                ct = cayennetypes[typ]
                dsize = ct['size']
                if not isinstance(dsize,list):
                    dsize = [dsize]                

                desc = ct['desc']
                if not isinstance(desc,list):
                    desc = [desc]
                fmt = ct['format']
                if not isinstance(fmt,list):
                    fmt = [fmt]
                mult = ct['mult']
                if not isinstance(mult,list):
                    mult = [mult]

                for x in range(0,len(dsize)):
                    buf = buffer[q:q+dsize[x]]
                    val = float(struct.unpack(fmt[x],buf)[0])
                    #print(str(val) + " * " + str(mult[x]))
                    val *= mult[x]
                    
                    finalname = self.GetFreeName(desc[x],resp)
                    resp[finalname] = val
                    q += dsize[x]

        return resp        

    #Extract binary data into a dict
    def Extract(self,buffer):
        if self.cayenne == True:
            return self.ExtractCayenne(buffer)

        resp = {}
        offset = 0                
        for s in range(0,len(self.patternparts)):
            step = self.patternparts[s]
            if isinstance(step,PatternMatch):            
                bufsize = step.size
                md = buffer[offset:offset+bufsize]
                offset += bufsize                             

                if step.format == "S":
                    #Read as string
                    st = md.decode('ascii')                                    
                    resp[step.name] = st.strip('\x00')
                else:
                    #Read as number
                    resp[step.name] = step.Transform(struct.unpack(step.format,md)[0])
            else:
                if step[0] == "=":                                
                    if buffer[offset] not in step[1]:
                        return None
                    offset += 1
                    continue
                    
                if step[0] == ".":
                    if offset >= len(buffer):
                        return None
                    offset += 1
                    continue                   

                #Extract Bitmask
                if step[0] == "B":
                    vl = int(buffer[offset])
                    for q in range(0,len(step[1])):
                        if step[1][q] != "":
                            if (vl & 1>>q) != 0:
                                resp[step[1][q]] = 1
                            else:
                                resp[step[1][q]] = 0

                    offset += 1

                #Extract Bitmask as String
                if step[0] == "S":
                    vl = int(buffer[offset])
                    for q in range(0,len(step[1])-1):

                        resp[step[1][0]] = ""
                        if step[1][q+1] != "":
                            if (vl & 1>>q) != 0:                                
                                if resp[step[1][0]] == "":
                                    resp[step[1][0]] = step[1][q]
                                else:
                                    resp[step[1][0]] += ", " + step[1][q]                           

                    offset += 1

        return resp
        
#Represents a payload that has arrived and needs to be decoded.
class Payload:
    def __init__(self,content,encoding=None):
        self.encoding = encoding
        if encoding is None:
            self.encoding = self.GuessEncoding(content)

        self.buffer = self.Decode(content)

    #Try to predict the encoding of the string
    def GuessEncoding(self,encoded):
        if " " in encoded:
            return "hex"

        search = encoded.lower()
        for q in range(0,len(search)):
            if ord(search[q]) > ord('f'):
                return "base64"

        return "base64"

    #Convert a text message into a binary one.
    def Decode(self,encoded):
        if self.encoding == "base64":
            return base64.b64decode(encoded)
        if self.encoding == "hex":
            dta = encoded.replace(" ","")
            if len(dta) % 2 != 0:
                return None
            
            bytevalues = []
            q = 0
            while q < len(dta):                
                #print("Hex Value: " + dta[q:q+2])
                val = int(dta[q:q+2],base=16)
                bytevalues.append(val)
                q += 2

            ba = bytearray(bytevalues)
            return bytes(ba)

        return None

#The main class used to decode LORA payloads.
class PayloadDecoder:
    #Create a new decoder, passing in a string that is either 'cayenne', the device ID, or a pattern to be matched.
    def __init__(self,name,library=None):
        self.patterns = []
        self.detail = None
        found = False

        #If this is a LIST, assume it's a list of patterns.
        if isinstance(name,list):
            for n in name:
                self.patterns.append(n)

        else:
            #Otherwise, it should be a single string.

            #If the user specified a device library path, load it.
            if library is not None:
                try:
                    f = open(library,'r')
                    listing = json.loads(f.read())
                    f.close()

                    #Search the library for a matching device name.
                    if name in listing:        
                        self.detail = {}    
                        #Copy additional device information into the dictionary
                        for d in listing[name]:
                            if d != "payloads":
                                self.detail[d] = listing[name][d]
                            
                        #A single device name might have many payloads.
                        for p in listing[name]['payloads']:
                            self.patterns.append(Pattern(p))

                except:
                    print("Failed To Load Library")
                    traceback.print_exc()
                    pass
                    
            #Assume the user has passed the pattern name
            if found == False:
                self.patterns.append(Pattern(name))

    #Decode a LORA message into a dictionary.
    def Parse(self,encoded):   
        #Get the raw bytes of the message.     
        buffer = encoded.buffer

        #Compare this to each of the patterns to find a match.
        for p in self.patterns:
            resp = p.Extract(buffer)
            if resp is not None:
                if self.detail is not None:
                    for d in self.detail:
                        if d not in resp:
                            resp[d] = self.detail[d]
                return resp

        return None

