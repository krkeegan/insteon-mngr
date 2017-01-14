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
            <h4>Configuration</h4>
            <form>
              <label for="user">Hub Username</label>
              <input type='text' class="form-control" id="user" value="{{attributes['user']}}">
              <label for="password">Hub Password</label>
              <input type='password' class="form-control" id="password" value="{{attributes['password']}}">
              <label for="ip">Hub IP</label>
              <input type='text' class="form-control" id="ip" value="{{attributes['ip']}}">
              Port(PLM)</br>
              <button type="submit" class="btn btn-default">Save</button>
            </form>
          </div>
          <div class="col-sm-4">
            <h4>Scenes</h4>
            <button type="button" class="btn btn btn-default btn-lg btn-block">View Scenes</button>
          </div>
          <div class="col-sm-4">
            <h4>Functions</h4>
            <button type="button" class="btn btn-default btn-lg btn-block">Scan Devices</button>
            <button type="button" class="btn btn-default btn-lg btn-block">Add Device</button>
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
