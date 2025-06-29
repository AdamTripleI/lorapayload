import lorapayload

pl = lorapayload.PayloadDecoder("[1][x92][1](Battery:B:*0.1)(Temperature:<H:*0.1)")
res = pl.Parse(lorapayload.Payload("AZIBMyUAAAAAAA==",encoding="base64"))
print(str(res))

pl = lorapayload.PayloadDecoder("cayenne")
res = pl.Parse(lorapayload.Payload("03 67 01 10 05 67 00 FF",encoding="hex"))
print(str(res))

res = pl.Parse(lorapayload.Payload("06 71 04 D2 FB 2E 00 00"))
print(str(res))

pl = lorapayload.PayloadDecoder("R718CT",library='lorapayloads.json')
res = pl.Parse(lorapayload.Payload("AZIBMyUAAAAAAA=="))
print(str(res))
