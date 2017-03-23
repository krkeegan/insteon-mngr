/* global $ */

function coreData (data, status, xhr) {
  if (status === 'success') {
    updateModemList(data)
    updateNavigation(data)
    updateModemPage(data)
    updateModemGroupPage(data)
    updateDevicePage(data)
    updateDeviceGroupPage(data)
  }
}

function linksData (data, status, xhr) {
  if (status === 'success') {
    if ($('tbody#definedLinks').length) {
      $('tbody#definedLinks').html('')
      for (var i = 0; i < data['definedLinks'].length; i++) {
        $('tbody#definedLinks').append(`
          <tr>
            <th scope='row'>${data['definedLinks'][i]['responder']}</th>
            <td>${data['definedLinks'][i]['data_1']}</td>
            <td>${data['definedLinks'][i]['data_2']}</td>
            <td>${data['definedLinks'][i]['status']}</td>
            <td>Fix/Delete/Edit</td>
          </tr>
        `)
      }
    }
    if ($('tbody#undefinedLinks').length) {
      $('tbody#undefinedLinks').html('')
      for (var i = 0; i < data['undefinedLinks'].length; i++) {
        $('tbody#undefinedLinks').append(`
          <tr>
            <th scope='row'>${data['undefinedLinks'][i]['responder']}</th>
            <td>${data['undefinedLinks'][i]['data_1']}</td>
            <td>${data['undefinedLinks'][i]['data_2']}</td>
            <td>Import/Delete</td>
          </tr>
        `)
      }
    }
    if ($('tbody#unknownLinks').length) {
      $('tbody#unknownLinks').html('')
      for (var i = 0; i < data['unknownLinks'].length; i++) {
        $('tbody#unknownLinks').append(`
          <tr>
            <th scope='row'>${data['unknownLinks'][i]['device']}</th>
            <td>Add Device/Delete Link</td>
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
          <td><a href='/modem/${address}'>View</a></td>
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
    $('a#navModem').attr('href', '/modem/' + modemAddress)
  }
  if ($('li#navModemGroup').length) {
    var modemGroup = getModemGroup()
    $('li#navModemGroup').html(`${data[modemAddress]['groups'][modemGroup]['name']} - ${modemGroup}`)
  }
  if ($('#navDevice').length) {
    var deviceAddress = getDeviceAddress()
    $('#navDevice').html(`${data[modemAddress]['devices'][deviceAddress]['name']} - ${deviceAddress}`)
  }
  if ($('a#navDevice').length) {
    $('a#navDevice').attr('href', '/modem/' + modemAddress + '/device/' + deviceAddress)
  }
  if ($('li#navDeviceGroup').length) {
    var deviceGroup = getDeviceGroup()
    $('li#navDeviceGroup').html(`${data[modemAddress]['devices'][deviceAddress]['groups'][deviceGroup]['name']} - ${deviceGroup}`)
  }
}

function updateModemPage (data) {
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
      <button type="submit" class="btn btn-default btn-block">
        Save Settings
      </button>
    `)
  }
  if ($('tbody#modemScenes').length) {
    $('tbody#modemScenes').html(``)
    for (var groupNumber in data[modemAddress]['groups']) {
      $('tbody#modemScenes').append(`
        <tr>
          <th scope='row'>${data[modemAddress]['groups'][groupNumber]['name']}</th>
          <td>${groupNumber}</td>
          <td>status</td>
          <td><a href='/modem/${modemAddress}/group/${groupNumber}'>View</a></td>
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
          <td><a href='/modem/${modemAddress}/device/${deviceAddress}'>View</a></td>
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
      <button type="submit" class="btn btn-default btn-block">
        Save Settings
      </button>
    `)
  }
}

function updateDevicePage (data) {
  var modemAddress = getModemAddress()
  if ($('form#deviceSettings').length) {
    var deviceAddress = getDeviceAddress()
    $('form#deviceSettings').html('')
    $('form#deviceSettings').append(createFormElement(
      'Device Name', 'name', 'text', data[modemAddress]['devices'][deviceAddress]['name'])
    )
    $('form#deviceSettings').append(createFormElement(
      'Device Address', 'name', 'text', deviceAddress, true)
    )
    $('form#deviceSettings').append(`
      <button type="submit" class="btn btn-default btn-block">
        Save Settings
      </button>
    `)
  }
  if ($('tbody#deviceGroups').length) {
    $('tbody#deviceGroups').html(``)
    for (var groupNumber in data[modemAddress]['devices'][deviceAddress]['groups']) {
      $('tbody#deviceGroups').append(`
        <tr>
          <th scope='row'>${data[modemAddress]['devices'][deviceAddress]['groups'][groupNumber]['name']}</th>
          <td>${groupNumber}</td>
          <td>status</td>
          <td><a href='/modem/${modemAddress}/device/${deviceAddress}/group/${groupNumber}'>View</a></td>
        </tr>
      `)
    }
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
    $('form#deviceGroupSettings').append(`
      <button type="submit" class="btn btn-default btn-block">
        Save Settings
      </button>
    `)
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

function getModemAddress () {
  var regex = /^\/modem\/([A-Fa-f0-9]{6})/
  return regex.exec(window.location.pathname)[1]
}

function getModemGroup () {
  var regex = /^\/modem\/[A-Fa-f0-9]{6}\/group\/([0-9]{1,3})/
  return regex.exec(window.location.pathname)[1]
}

function getDeviceAddress () {
  var regex = /^\/modem\/[A-Fa-f0-9]{6}\/device\/([A-Fa-f0-9]{6})/
  return regex.exec(window.location.pathname)[1]
}

function getDeviceGroup () {
  var regex = /^\/modem\/[A-Fa-f0-9]{6}\/device\/[A-Fa-f0-9]{6}\/group\/([0-9]{1,3})/
  return regex.exec(window.location.pathname)[1]
}

$(document).ready(function () {
  $.getJSON('/api', coreData)
  if ($('tbody#definedLinks').length) {
    var path = window.location.pathname.replace(/\/$/, '')
    $.getJSON('/api' + path + '/links', linksData)
  }
})
