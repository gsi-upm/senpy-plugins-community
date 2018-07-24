# Senpy Plugin Taiger

Service that analyzes sentiments from social posts written in Spanish or English.


## Usage

To use this plugin, you should use a GET Requests with the following possible params:
Params:	
- Input: text to analyse.(required)
- Endpoint: Enpoint to the Taiger service.

## Example of Usage

Example request: 
```
http://senpy.cluster.gsi.dit.upm.es/api/?algo=sentiment-taiger&inputText=This%20is%20amazing
```

Example respond: This plugin follows the standard for the senpy plugin response. For more information, please visit [senpy documentation](http://senpy.readthedocs.io). Specifically, NIF API section. 

This plugin supports **python2.7** and **python3**.

![alt GSI Logo][logoGSI]

[logoGSI]: http://www.gsi.dit.upm.es/images/stories/logos/gsi.png "GSI Logo"

