# LoraPayload

## Introduction

This Python module decodes LORA/LORAWan payloads into dictionaries that break down the values (usually from sensors).

This does not decode/decrypt the lora packet itself, like you'll see in packages such as **python-lora**. Instead, it takes the already-decrypted payload data and decodes the individual readings in cases where custom decoders can't be used in the Chirpstack server.

## Usage

### Using a Known Device

The module includes a **very** incomplete collection of device names that have pre-made Payload Decoding Expressions.

The example below is used for the NetVox R718CT temperature sensor.

```
import lorapayload

#Create a payload decoder
pl = lorapayload.PayloadDecoder("R718CT",library='lorapayloads.json')

#Parse a payload (auto-calculate the encoding)
decoded = pl.Parse(lorapayload.Payload("AZIBMyUAAAAAAA=="))

#{'Battery': 5.1000000000000005, 'Temperature': 3.7, 'LowTempAlarm': 0, 'HighTempAlarm': 0, 'manufacturer': 'Netvox', 'model': 'R718CT'}
```

### Using a Custom Decoding String

The library allows you to use custom decoding strings

```
import lorapayload

#Create a payload decoding using a custom string
pl = lorapayload.PayloadDecoder("[1][x92][1](Battery:B:*0.1)(Temperature:<H:*0.1)")

#Parse the payload, enforcing a base64 encoding method.
decoded = pl.Parse(lorapayload.Payload("AZIBMyUAAAAAAA==",encoding="base64"))

#{'Battery': 5.1000000000000005, 'Temperature': 3.7}
```

### Using CayenneLPP

The library also supports the CayennaLPP format, which is a common self-describing payload format.

```
import lorapayload

#Create a payload decoding CayenneLPP
pl = lorapayload.PayloadDecoder("cayenne")

#Parse the payload
decoded = pl.Parse(lorapayload.Payload("03 67 01 10 05 67 00 FF",encoding="hex"))

#{'Temperature': 27.200000000000003, 'Temperature2': 25.5}
```

## Decoding Strings

**Decoding Strings** define the _patterns_ that the decoder searches for and uses to extract data. These are similar in concept to regular expressions. A single device may have several different _patterns_ associated with it if it sends a variety of messages or has changed it's protocol over time. Each pattern is tried until one is found that matches the payload data.

Decoding strings are made up of the following parts...

### Periods

A period (.) character matches with _any_ byte value.

### Square Brackets (Byte Value Matches)

Square brackets define the value of a byte that must match exactly. For example, **[0]** indicates that the byte value _must_ be zero. This can be a comma-delimited list of values if more than one is acceptable (ie. [0,1,2] would accept byte values of zero, one or two). Any number starting with the character 'x' will be treated as hexidecimal (ie [xA0] would be 160).

### Round Brackets (Capture Regions)

Round brackets indicate a value you would like to capture. Inside the round brackets should be a _name_, a _struct format_ and optionally a set of _transformations_, delimited by the ':' character.

The _struct format_ is the text format used in the Python **struct.unpack** function that can read the value from a byte stream. For example, 'B' for a byte, '>h' for a big-endian short int etc. Please see the struct documentation for more.

The _transformations_ are a symbol (such as '+','*','-' or '/') followed by a numeric amount. You can include multiple of these transformations. They are applied from left-to-right on the value.

For example, 'Active:B' would be a byte named 'Active'.

'Temperature:>h:*0.1' would read a temperature as a two-byte signed integer and then multiply it by 0.1.

'Temperature:>h:*0.1*1.8+32' would read that same temperature and convert it from _celcius_ to _fahrenheit_.

### Curly Brackets (Bitmasks)

Curly brackets/braces indicate a _bitmask_. In this case, the byte is assumed to contain alerts or similar status indicators in each bit of the byte. Enter the names of each different state/status as a comma-delimited list.

For example, {Low Alarm,High Alarm,Sensor Error} would treat the first bit of the byte as a Low Alarm indicator, the second bit as a High Alarm and the third as a Sensor Error indicator.

### Putting It Together

Below is an example of a decoder for the R718CT...

```
[1][x92][1](Battery:B:*0.1)(Temperature:<h:*0.1){LowTempAlarm,HighTempAlarm}
```

The pattern says....

    The first byte should be 1,
    The second byte should be 92 hex, or 146 decimal,
    The third byte should be 1,
    The next byte indicates the _battery voltage_, and should be multiplied by 0.1,
    The next two bytes give the _temperature_, should be read as an _unsigned short_, and the result should be multiplied by 0.1,
    The next byte contains a bitmask - byte 1 is the Low Temperature Alarm, while byte 2 is the High Temperature Alarm.

When run in the code below...

```
#Create a payload decoder
pl = lorapayload.PayloadDecoder(["[1][x92][0](SVersion:B:*0.1)(HVersion:B:*0.1)(Date:<L)","[1][x92][1](Battery:B:*0.1)(Temperature:<h:*0.1){LowTempAlarm,HighTempAlarm}"])
decoded = pl.Parse(lorapayload.Payload("AZIBMyUAAAAAAA=="))
```

The final 'decoded' list would contain...

```
{
    'Battery': 5.1,
    'Temperature': 3.7,
    'LowTempAlarm': 0,
    'HighTempAlarm': 0
}
```