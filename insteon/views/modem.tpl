<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Insteon Link Manager</title>

    <!-- Bootstrap -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css" integrity="sha384-rHyoN1iRsVXV4nD0JutlnGaslCJuC7uwjduW9SVrLvRYooPp2bWYgmgJQIXwl/Sp" crossorigin="anonymous">
    <link rel="stylesheet" href="/static/style.css">

    <!-- HTML5 shim and Respond.js for IE8 support of HTML5 elements and media queries -->
    <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
    <!--[if lt IE 9]>
      <script src="https://oss.maxcdn.com/html5shiv/3.7.3/html5shiv.min.js"></script>
      <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
    <![endif]-->
  </head>
  <body>
    % include('header', paths=[{'path':'modem', 'name': 'name - ' + device_id},])

    <div class="row">
      <div class="col-md-10 col-md-offset-1">
        <div class="row">
          <div class="col-sm-4">
            <h4>Settings</h4>
            <form>
              <label for="user">Hub Username</label>
              <input type='text' class="form-control" id="user" value="{{attributes['user']}}">
              <label for="password">Hub Password</label>
              <input type='password' class="form-control" id="password" value="{{attributes['password']}}">
              <label for="ip">Hub IP</label>
              <input type='text' class="form-control" id="ip" value="{{attributes['ip']}}">
              <label for="port">Port</label>
              <input type='text' class="form-control" id="port" value="{{attributes['port']}}">
              <label for="dev_addr_str">Device Address</label>
              <input type='text' class="form-control" id="dev_addr_str" value="{{attributes['dev_addr_str']}}" readonly>
              </br>
              <button type="submit" class="btn btn-default btn-block">Save Settings</button>
              <h4>Functions</h4>
              <button type="submit" class="btn btn-default btn-block">Scan Devices</button>
              <button type="submit" class="btn btn-default btn-block">Sync Links</button>
              <button type="submit" class="btn btn-default btn-block">Delete Links</button>
            </form>
          </div>
          <div class="col-sm-4">
            <div class="height-limited">
              <h4>Scenes</h4>
              % for group in groups:
                % for key, value in group.items():
                  <a href='/modem/{{attributes['dev_addr_str']}}/group/{{key}}'><!--Add Group Name--> - {{key}}</a></br>
                % end
              % end
            </div>
          </div>
          <div class="col-sm-4">
            <div class="height-limited">
              <h4>Devices</h4>
              % for device in devices:
                % for key, value in device.items():
                  <a href='/modem/{{attributes['dev_addr_str']}}/device/{{key}}'><!--Add Group Name--> - {{key}}</a></br>
                % end
              % end
            </div>
          </div>
        </div>
      </div>
    </div>



    <!-- jQuery (necessary for Bootstrap's JavaScript plugins) -->
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>
    <!-- Include all compiled plugins (below), or include individual files as needed -->
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>
  </body>
</html>
