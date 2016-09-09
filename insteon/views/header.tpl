<ol class="breadcrumb">
  <li><a href="/">Home</a></li>
  % location_track = 0
  % for location in paths:
    % location_track += 1
    % if location_track == len(paths):
      <li class="active">{{location['name']}}</li>
    % else:
      <li><a href="{{location['path']}}">{{location['name']}}</a></li>
    % end
  % end
</ol>
