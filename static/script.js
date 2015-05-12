(function() {

 function getBaseUrl() {
  var url = location.protocol + '//' + location.hostname;
  if (location.port)
   url += ':' + location.port;
  console.log(url);
  return url;
 }

 function ajax(url, callback) {
  var xhr = new XMLHttpRequest();
  xhr.open("get", url, true);
  xhr.onreadystatechange = function() {
   if (xhr.readyState == 4 && xhr.status == 200)
    callback(xhr.responseText);
  };
  xhr.send(null);
 }

 function log(msg) {
  var ele = document.getElementById(state.logElementId);
  ele.innerHTML += '<div>' + msg + '</div>';
  ele.scrollTop = ele.scrollHeight;
 }

 function result(msg) {
  document.getElementById(state.resultElementId).innerHTML = msg;
 }

 var state = {
  logElementId: null,
  resultElementId: null,
  noResultText: '',
  plugin: null,
  taskKey: null,
 };

 window.pmcaInit = function(logElementId, resultElementId) {
  state.logElementId = logElementId;
  state.resultElementId = resultElementId;
  state.noResultText = document.getElementById(resultElementId).innerHTML;
  loadPlugin();
 };
 function loadPlugin() {
  log('Loading plugin');
  document.body.innerHTML += '<object id="pmcaPlugin" type="application/x-pmcadownloader" width="1" height="1" style="position:absolute;left:0;top:0;"><param name="onload" value="pmcadl_ev_plugin_loaded"></object>';
 }
 window.pmcadl_ev_plugin_loaded = function() {
  log('Plugin loaded');
  state.plugin = document.getElementById('pmcaPlugin');
 };

 function pluginMethod(method, data) {
  log('Calling plugin (method = ' + method + ', data = ' + JSON.stringify(data) + ')');
  var response = state.plugin.pmcadpMethod(method, data);
  log('Plugin response: ' + JSON.stringify(response));
 }

 var errorCallbacks = [
  ['pmcadl_ev_detect_none_device', 'No device detected'],
  ['pmcadl_ev_detect_multi_devices', 'Multiple devices detected'],
  ['pmcadl_ev_detect_pmb', 'Pmb detected'],// ???
  ['pmcadl_ev_detect_pmh', 'Pmh detected'],// ???
  ['pmcadl_ev_detect_device_busy', 'Device busy'],
  ['pmcadl_ev_unknown_error', 'Unknown error'],
  ['pmcadl_ev_failed_deviceinfo_dl', 'Device info download failed'],
  ['pmcadl_ev_failed_deviceinfo_read', 'Device info read failed'],
  ['pmcadl_ev_other_instance_exists', 'Other instance detected'],
  ['pmcadl_ev_failed_mode_switch', 'Mode switch'],
  ['pmcadl_ev_usb_connection_error', 'USB connection'],
  ['pmcadl_ev_network_connection_error', 'Network connection'],
  ['pmcadl_ev_error_from_device', 'Device error'],
 ];
 for (var i=0; i<errorCallbacks.length; i++) {
  var err = errorCallbacks[i];
  window[err[0]] = function(arg) {
   log('Error: ' + err[1] + ' (arg = ' + JSON.stringify(arg) + ')');
  };
 }

 window.pmcaDownload = function(blobKey) {
  if (!state.plugin)
   return log('Error: Plugin not loaded');
  startTask(blobKey);
 }
 function startTask(blobKey) {
  result(state.noResultText);
  log("Starting task (blobKey = " + blobKey + ")");
  var url = '/ajax/task/start';
  if (blobKey)
   url += '/' + blobKey
  ajax(url, function(data) {
   state.taskKey = JSON.parse(data).id;
   log("Got task key (taskKey = " + state.taskKey + ")");
   pluginCancel();
  });
 }
 function pluginCancel() {
  log('Cancelling plugin');
  pluginMethod('pmcadl_request_sequence_cancel', {});
 }
 window.pmcadl_ev_finish_to_cancel_successfully = function() {
  log('Plugin cancelled');
  startDownload(state.taskKey);
 };
 function startDownload(taskKey) {
  log('Starting download to camera');
  pluginMethod('pmcadl_request_sequence_start', {'trigger_url': getBaseUrl() + '/camera/xpd/' + taskKey});
 }
 window.pmcadl_ev_progress = function(arg) {
  log('Download progress (' + JSON.stringify(arg) + ')');
 };
 window.pmcadl_ev_complete_download = function() {
  log('Download completed');
  getTaskResponse(state.taskKey);
 };
 function getTaskResponse(taskKey) {
  log('Getting camera response');
  ajax('/ajax/task/view/' + taskKey, function(data) {
   log("Finished task");
   result(data);
  });
 }

})();
