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

function generateDataSelect (currentValue, dataDetails) {
  var ret = $(`
  <label class="col-md-4 col-form-label label-sm">
    ${dataDetails['name']}
  </label>
  <div class="col-md-8">
    <select class="form-control input-sm"/>
  </div>
  `)
  for (var key in dataDetails['values']) {
    var option = $('<option>').attr('value', dataDetails['values'][key]).text(key)
    if (currentValue === dataDetails['values'][key]) {
      option.attr('selected', true)
    }
    ret.find('select').append(option)
  }
  return ret
}

function generateResponderSelect (responderID) {
  var ret = $('<select class="form-control input-sm responderInput"/>')
  var responders = getResponderList()
  for (var key in responders) {
    var deviceID = responders[key]['deviceID']
    var deviceName = responders[key]['name']
    var option = $('<option>').attr('value', deviceID).text(deviceName + ' - ' + deviceID)
    // This may not be suffcient, we might need to match group here too
    if (responderID === deviceID) {
      option.attr('selected', true)
    }
    ret.append(option)
  }
  return ret
}

function outputDefinedLinkRow (data) {
  var ret = $(`
    <tr id="definedLinksRow">
      <th class="row" scope='row'>
      <label class="visible-sm visible-xs col-form-label">
        &nbsp;
      </label>
      </th>
      <td class="row form-group definedLinksData1">
      </td>
      <td class="row form-group definedLinksData2">
      </td>
      <td class="row">
        <label class="visible-sm visible-xs col-form-label">
          &nbsp;
        </label>
        <button type="button" class="btn btn-default btn-sm definedLinkFix" style="display: none">
          Fix
        </button>
        <button type="button" class="btn btn-default btn-sm definedLinkEdit">
          Edit
        </button>
        <button type="button" class="btn btn-danger btn-sm definedLinkDelete">
          Delete
        </button>
        <button type="button" class="btn btn-success btn-sm definedLinkSave" style="display: none">
          Save
        </button>
        <button type="button" class="btn btn-default btn-sm definedLinkCancel" style="display: none">
          Cancel
        </button>
      </td>
    </tr>
  `)
  for (var key in data) {
    ret.data(key, data[key])
  }
  if (data['status'] === 'Broken') {
    ret.find('.definedLinkEdit').show()
    ret.find('.definedLinkEdit').hide()
    ret.find('tr').addClass('danger')
  }
  var linkDetails = getDeviceLinkDetails(
    data['responder_id'],
    data['data_3']
  )
  ret.find('th').find('label').after(generateResponderSelect(data['responder_id']))
  ret.find('.definedLinksData1').append(generateDataSelect(data['data_1'],
                                        linkDetails['data_1']))
  ret.find('.definedLinksData2').append(generateDataSelect(data['data_2'],
                                        linkDetails['data_2']))
  ret.find('select').attr('disabled', true)
  return ret
}

function linksData (data, status, xhr) {
  if (status === 'success') {
    if ($('tbody#definedLinks').length) {
      $('tbody#definedLinks').html('')
      for (var i = 0; i < data['definedLinks'].length; i++) {
        $('tbody#definedLinks').append(outputDefinedLinkRow(data['definedLinks'][i]))
      }
      $('.definedLinkEdit').click(function () {
        $(this).parents('tr').find('select').removeAttr('disabled')
        $(this).parents('tr').find('.definedLinkEdit').hide()
        $(this).parents('tr').find('.definedLinkDelete').hide()
        $(this).parents('tr').find('.definedLinkSave').show()
        $(this).parents('tr').find('.definedLinkCancel').show()
      })
      $('.definedLinkCancel').click(function () {
        // Reset data fields back to how they appeared on load
        $(this).parents('tr').find('.responderInput').val(function () {
          return $(this).find('option').filter(function () {
            return $(this).prop('defaultSelected')
          }).val()
        })
        $(this).parents('tr').find('.responderInput').trigger('change')
        $(this).parents('tr').find('select').val(function () {
          return $(this).find('option').filter(function () {
            return $(this).prop('defaultSelected')
          }).val()
        })
        $(this).parents('tr').find('select').attr('disabled', true)
        $(this).parents('tr').find('.definedLinkEdit').show()
        $(this).parents('tr').find('.definedLinkDelete').show()
        $(this).parents('tr').find('.definedLinkSave').hide()
        $(this).parents('tr').find('.definedLinkCancel').hide()
      })
      $('.responderInput').change(function () {
        // Update Data Fields when Responder is Changed
        var linkDetails = getDeviceLinkDetails(
          $(this).find(':selected').val(),
          $(this).find(':selected').data('data_3')
        )
        var dataRow = $(this).parents('tr')
        dataRow.find('.definedLinksData1').html(
          generateDataSelect(dataRow.data('data_1'), linkDetails['data_1'])
        )
        dataRow.find('.definedLinksData2').html(
          generateDataSelect(dataRow.data('data_2'), linkDetails['data_2'])
        )
      })
    } // End Defined Links
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
                id="undefinedLinkImport" class="btn btn-default"
              >
                Import
              </button>
              <button type="button" class="btn btn-danger undefinedLinkDelete">
                Delete
              </button>
            </td>
          </tr>
        `)
      }
      $('.undefinedLinkImport').click(function () {
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
