/* global $ */
var coreJSON = {}

function coreData (data, status, xhr) {
  if (status === 'success') {
    coreJSON = data
    updateModemList(data)
    updateNavigation(data)
    updateModemPage(data)
    updateModemGroupPage(data)
    updateDeviceGroupPage(data)
    if ($('tbody#definedLinks').length) {
      var path = window.location.pathname.replace(/\/$/, '')
      $.getJSON(path + '/links.json', linksData)
    }
  }
}

function getDeviceLinkDetails (deviceID, groupID) {
  var ret = {}
  if (coreJSON.hasOwnProperty(deviceID)) {
    ret = coreJSON[deviceID]
    if (ret['groups'].hasOwnProperty(groupID)) {
      ret = ret['groups'][groupID]
    }
  } else {
    for (var modem in coreJSON) {
      if (coreJSON[modem]['devices'].hasOwnProperty(deviceID)) {
        ret = coreJSON[modem]['devices'][deviceID]
        if (ret['groups'].hasOwnProperty(groupID)) {
          ret = ret['groups'][groupID]
        }
        break
      }
    }
  }
  return ret
}

function addResponder (ret, deviceID, group, deviceData) {
  if (deviceData['responder'] === true) {
    // Key is used solely to catch duplicates
    ret[deviceID + '_' + group] = {
      'name': deviceData['name'],
      'group_number': group,
      'deviceID': deviceID
    }
  }
  return ret
}

function getResponderList () {
  var ret = {}
  for (var modem in coreJSON) {
    ret = addResponder(ret, modem, 1, coreJSON[modem])
    for (var modemGroup in coreJSON[modem]['groups']) {
      ret = addResponder(ret, modem, modemGroup, coreJSON[modem]['groups'][modemGroup])
    }
    for (var device in coreJSON[modem]['devices']) {
      ret = addResponder(ret, device, 1, coreJSON[modem]['devices'][device])
      for (var deviceGroup in coreJSON[modem]['devices'][device]['groups']) {
        ret = addResponder(ret, device, deviceGroup, coreJSON[modem]['devices'][device]['groups'][deviceGroup])
      }
    }
  }
  return ret
}

function linksData (data, status, xhr) {
  if (status === 'success') {
    if ($('tbody#definedLinks').length) {
      $('tbody#definedLinks').html('')
      for (var i = 0; i < data['definedLinks'].length; i++) {
        var fixButton = ''
        var rowClass = ''
        if (data['definedLinks'][i]['status'] === 'Broken') {
          fixButton = `
            <button type="button" id="definedLinkFix" class="btn btn-default btn-xs">
              Fix
            </button>
            `
          rowClass = 'danger'
        }
        var linkDetails = getDeviceLinkDetails(
          data['definedLinks'][i]['responder_id'],
          data['definedLinks'][i]['data_3']
        )
        var responderInput = $('<select disabled="disabled"/>')
        var responders = getResponderList()
        for (var key in responders) {
          var deviceID = responders[key]['deviceID']
          var deviceName = responders[key]['name']
          var option = $('<option>').attr('value', deviceID).text(deviceName + ' - ' + deviceID)
          // This may not be suffcient, we might need to match group here too
          if (data['definedLinks'][i]['responder_id'] === deviceID) {
            option.attr('selected', true)
          }
          responderInput.append(option)
        }
        responderInput = $('<div>').append(responderInput).html()
        var data1Input = $('<select disabled="disabled"/>')
        for (var key in linkDetails['data_1']['values']) {
          var option = $('<option>').attr('value', linkDetails['data_1']['values'][key]).text(key)
          if (data['definedLinks'][i]['data_1'] === linkDetails['data_1']['values'][key]) {
            option.attr('selected', true)
          }
          data1Input.append(option)
        }
        data1Input = $('<div>').append(data1Input).html()
        var data2Input = $('<select disabled="disabled"/>')
        for (var key in linkDetails['data_2']['values']) {
          var option = $('<option>').attr('value', linkDetails['data_2']['values'][key]).text(key)
          if (data['definedLinks'][i]['data_2'] === linkDetails['data_2']['values'][key]) {
            option.attr('selected', true)
          }
          data2Input.append(option)
        }
        data2Input = $('<div>').append(data2Input).html()
        $('tbody#definedLinks').append(`
          <tr id="definedLinksRow${i}" class="${rowClass}">
            <th scope='row'>${responderInput}</th>
            <td id="definedLinksData1${i}">${linkDetails['data_1']['name']}: ${data1Input}</td>
            <td id="definedLinksData2${i}">${linkDetails['data_2']['name']}: ${data2Input}</td>
            <td>
              ${fixButton}
              <button type="button" id="definedLinkEdit" class="btn btn-default btn-xs">
                Edit
              </button>
              <button type="button" id="definedLinkDelete" class="btn btn-default btn-xs">
                Delete
              </button>
            </td>
          </tr>
        `)
      }
    }
    if ($('tbody#undefinedLinks').length) {
      $('tbody#undefinedLinks').html('')
      for (var i = 0; i < data['undefinedLinks'].length; i++) {
        var linkDetails = getDeviceLinkDetails(
          data['undefinedLinks'][i]['responder_id'],
          data['undefinedLinks'][i]['data_3']
        )
        $('tbody#undefinedLinks').append(`
          <tr>
            <th scope='row'>${data['undefinedLinks'][i]['responder_name']} - ${data['undefinedLinks'][i]['responder_id']}</th>
            <td>${linkDetails['data_1']['name']}: ${data['undefinedLinks'][i]['data_1']}</td>
            <td>${linkDetails['data_2']['name']}: ${data['undefinedLinks'][i]['data_2']}</td>
            <td>
              <button type="button"
                address="${data['undefinedLinks'][i]['responder_id']}"
                data_1="${data['undefinedLinks'][i]['data_1']}"
                data_2="${data['undefinedLinks'][i]['data_2']}"
                data_3="${data['undefinedLinks'][i]['data_3']}"
                id="undefinedLinkImport" class="btn btn-default btn-xs"
              >
                Import
              </button>
              <button type="button" id="undefinedLinkDelete" class="btn btn-default btn-xs">
                Delete
              </button>
            </td>
          </tr>
        `)
      }
      $('#undefinedLinkImport').click(function () {
        var jsonData = {
          'address': $(this).attr('address'),
          'group': parseInt($(this).attr('group')),
          'data_1': parseInt($(this).attr('data_1')),
          'data_2': parseInt($(this).attr('data_2')),
          'data_3': parseInt($(this).attr('data_3'))
        }
        var path = window.location.pathname.replace(/\/$/, '')
        $.ajax({
          url: path + '/links/definedLinks.json',
          method: 'POST',
          data: JSON.stringify(jsonData),
          contentType: 'application/json; charset=utf-8',
          dataType: 'json',
          success: linksData
        })
      })
    }
    if ($('tbody#unknownLinks').length) {
      $('tbody#unknownLinks').html('')
      for (var i = 0; i < data['unknownLinks'].length; i++) {
        $('tbody#unknownLinks').append(`
          <tr>
            <th scope='row'>${data['unknownLinks'][i]['device']}</th>
            <td>
            <button type="button" id="unknownLinkAdd" class="btn btn-default btn-xs">
              Add Device
            </button>
            <button type="button" id="unknownLinkDelete" class="btn btn-default btn-xs">
              Delete
            </button>
            </td>
          </tr>
        `)
      }
    }
  }
}

function updateModemList (data) {
  if ($('tbody#list_modems').length) {
    $('tbody#list_modems').html('')
    for (var address in data) {
      $('tbody#list_modems').append(`
        <tr>
          <th scope='row'>${data[address]['name']}</th>
          <td>${address}</td>
          <td>status</td>
          <td><a href='/modems/${address}'>View</a></td>
        </tr>
      `)
    }
  }
}

function updateNavigation (data) {
  var modemAddress = getModemAddress()
  if ($('#navModem').length) {
    $('#navModem').html(`${data[modemAddress]['name']} - ${modemAddress}`)
  }
  if ($('a#navModem').length) {
    $('a#navModem').attr('href', '/modems/' + modemAddress)
  }
  if ($('li#navModemGroup').length) {
    var modemGroup = getModemGroup()
    $('li#navModemGroup').html(`${data[modemAddress]['groups'][modemGroup]['name']} - ${modemGroup}`)
  }
  if ($('li#navDeviceGroup').length) {
    var deviceGroup = getDeviceGroup()
    var deviceAddress = getDeviceAddress()
    $('li#navDeviceGroup').html(`${data[modemAddress]['devices'][deviceAddress]['groups'][deviceGroup]['name']} - ${deviceAddress} - ${deviceGroup}`)
  }
}

function updateModemSettings (data) {
  var modemAddress = getModemAddress()
  if ($('form#modemSettings').length) {
    $('form#modemSettings').html('')
    $('form#modemSettings').append(createFormElement(
      'Modem Name', 'name', 'text', data[modemAddress]['name'])
    )
    $('form#modemSettings').append(createFormElement(
      'Modem Address', 'address', 'text', modemAddress, true)
    )
    var hubInputList = [
      ['Hub Username', 'user', 'text', data[modemAddress]['user']],
      ['Hub Password', 'password', 'text', data[modemAddress]['password']],
      ['Hub IP Address', 'ip', 'text', data[modemAddress]['ip']]
    ]
    for (var i = 0; i < hubInputList.length; i++) {
      $('form#modemSettings').append(createFormElement(
        hubInputList[i][0],
        hubInputList[i][1],
        hubInputList[i][2],
        hubInputList[i][3]
      ))
    }
    $('form#modemSettings').append(createFormElement(
      'Modem Port', 'port', 'text', data[modemAddress]['port'])
    )
    $('form#modemSettings').append(`
      <button type="button" id="modemSettingsSubmit" class="btn btn-default btn-block">
        Save Settings
      </button>
    `)
    $('#modemSettingsSubmit').click(function () {
      var jsonData = {}
      jsonData[modemAddress] = constructJSON(['name', 'user', 'password', 'ip', 'port'])
      $.ajax({
        url: '/modems.json',
        method: 'PATCH',
        data: JSON.stringify(jsonData),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: [updateModemSettings, updateNavigation]
      })
    })
  }
}

function updateModemPage (data) {
  var modemAddress = getModemAddress()
  updateModemSettings(data)
  if ($('tbody#modemScenes').length) {
    $('tbody#modemScenes').html(``)
    for (var groupNumber in data[modemAddress]['groups']) {
      $('tbody#modemScenes').append(`
        <tr>
          <th scope='row'>${data[modemAddress]['groups'][groupNumber]['name']}</th>
          <td>${groupNumber}</td>
          <td>status</td>
          <td><a href='/modems/${modemAddress}/groups/${groupNumber}'>View</a></td>
        </tr>
      `)
    }
  }
  if ($('tbody#modemDevices').length) {
    for (var deviceAddress in data[modemAddress]['devices']) {
      $('tbody#modemDevices').append(`
        <tr>
          <th scope='row'>${data[modemAddress]['devices'][deviceAddress]['name']}</th>
          <td>${deviceAddress}</td>
          <td>status</td>
          <td><a href='/modems/${modemAddress}/devices/${deviceAddress}'>View</a></td>
        </tr>
      `)
    }
  }
}

function updateModemGroupPage (data) {
  var modemAddress = getModemAddress()
  if ($('form#modemGroupSettings').length) {
    var groupNumber = getModemGroup()
    $('form#modemGroupSettings').html('')
    $('form#modemGroupSettings').append(createFormElement(
      'Scene Name', 'name', 'text', data[modemAddress]['groups'][groupNumber]['name'])
    )
    $('form#modemGroupSettings').append(`
      <button type="button" id="modemGroupSettingsSubmit" class="btn btn-default btn-block">
        Save Settings
      </button>
    `)
    $('#modemGroupSettingsSubmit').click(function () {
      var jsonData = {}
      jsonData[groupNumber] = constructJSON(['name'])
      $.ajax({
        url: '/modems/' + modemAddress + '/groups.json',
        method: 'PATCH',
        data: JSON.stringify(jsonData),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: [updateModemGroupPage, updateNavigation]
      })
    })
  }
}

function updateDeviceGroupPage (data) {
  var modemAddress = getModemAddress()
  if ($('form#deviceGroupSettings').length) {
    var deviceAddress = getDeviceAddress()
    var deviceGroup = getDeviceGroup()
    $('form#deviceGroupSettings').html('')
    $('form#deviceGroupSettings').append(createFormElement(
      'Group Name', 'name', 'text', data[modemAddress]['devices'][deviceAddress]['groups'][deviceGroup]['name'])
    )
    $('form#deviceSettings').append(createFormElement(
      'Device Address', 'name', 'text', deviceAddress, true)
    )
    $('form#deviceGroupSettings').append(`
      <button type="button" id="deviceGroupSettingsSubmit" class="btn btn-default btn-block">
        Save Settings
      </button>
    `)
    $('#deviceGroupSettingsSubmit').click(function () {
      var jsonData = {}
      jsonData[deviceGroup] = constructJSON(['name'])
      $.ajax({
        url: '/modems/' + modemAddress + '/devices/' + deviceAddress + '/groups.json',
        method: 'PATCH',
        data: JSON.stringify(jsonData),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: [updateModemGroupPage, updateNavigation]
      })
    })
  }
  if ($('tbody#deviceGroups').length) {
    $('tbody#deviceGroups').html(``)
    for (var groupNumber in data[modemAddress]['devices'][deviceAddress]['groups']) {
      $('tbody#deviceGroups').append(`
        <tr>
          <th scope='row'>${data[modemAddress]['devices'][deviceAddress]['groups'][groupNumber]['name']}</th>
          <td>${groupNumber}</td>
          <td>status</td>
          <td><a href='/modems/${modemAddress}/devices/${deviceAddress}/groups/${groupNumber}'>View</a></td>
        </tr>
      `)
    }
  }
}

function createFormElement (label, id, type, value, readOnly) {
  var labelElement = $('<label></label>')
  labelElement.html(label)
  labelElement.attr('for', id)
  var inputElement = $('<input class="form-control"></input>')
  inputElement.prop('type', type)
  inputElement.attr('id', id)
  inputElement.attr('name', id)
  inputElement.attr('value', value)
  if (readOnly) {
    inputElement.attr('readonly', true)
  }
  var divElement = $('<div></div>')
  divElement.append(labelElement, inputElement)
  return divElement.html()
}

function constructJSON (list) {
  var ret = {}
  for (var i = 0; i < list.length; i++) {
    ret[list[i]] = $('input#' + list[i]).val()
  }
  return ret
}

function getModemAddress () {
  var regex = /^\/modems\/([A-Fa-f0-9]{6})/
  return regex.exec(window.location.pathname)[1]
}

function getModemGroup () {
  var regex = /^\/modems\/[A-Fa-f0-9]{6}\/groups\/([0-9]{1,3})/
  return regex.exec(window.location.pathname)[1]
}

function getDeviceAddress () {
  var regex = /^\/modems\/[A-Fa-f0-9]{6}\/devices\/([A-Fa-f0-9]{6})/
  return regex.exec(window.location.pathname)[1]
}

function getDeviceGroup () {
  var regex = /^\/modems\/[A-Fa-f0-9]{6}\/devices\/[A-Fa-f0-9]{6}\/groups\/([0-9]{1,3})/
  return regex.exec(window.location.pathname)[1]
}

$(document).ready(function () {
  $.getJSON('/modems.json', coreData)
})
