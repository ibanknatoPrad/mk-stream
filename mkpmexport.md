# mkpmexport
Export your model-kartei personal messages to local files.

## usage: 

use python3 to run the script
should run in windows but not tested.

either set script to executable or run it
```
python3 mkmail.py
```


## prerequisits:

python3

requests
```
pip install requests
```

bs4
```
pip install bs4
```

## configuration

the .ini file must be edited first:
```
[credentials]
user=  <- your model-kartei user id
pass=  <- your model-kartei password

[mails]
base=./mails <- can be absolute or relative path where all the messages and attachments are written
images=true <- if true or 't' it will mirror image files too. Set to empty of 'f' or 'false' to disable
```
