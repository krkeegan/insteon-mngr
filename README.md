# The Problem
The Insteon Hub can:
- control devices (on/off)
- manage device attributes (default on levels and ramp rates)
- link devices to hub scenes
- provide access through the Insteon Restful API

The Insteon Hub cannot:
- __manage links between devices in your network!__

Recently I have learned that Insteon has become very stingy with handing out API keys, with some users waiting weeks to months.

Others have also expressed a desire not to rely on a cloud based service for home automation because of potential security and privacy concerns as well as a lack of reliability of the cloud service.

# The Goal
Initially, the goal was to create a simple interface for defining, scanning, and managing the links between the devices on your network.  With the hope of using the Insteon API to enable home automation platforms such as Home Assistant https://github.com/balloob/home-assistant to add insteon support.  

Now this project has expanded slightly to add support for local control of Insteon devices.

My hope is to keep this project tight and focused.  The Insteon stack and protocol is a mess and would quickly engulf this project if I tried to add support for all Insteon features.  Instead, I would like to add the minimal amount of support necessary to enable:
- device link management
- support for home-assistant or other home automation platforms

# Status
A long way from being done.  I have taken much of the code from other half-completed (or less) projects that I have started.
