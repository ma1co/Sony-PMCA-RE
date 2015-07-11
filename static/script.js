(function() {

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
  var result = state.plugin.pmcadpMethod(method, data)['pmcadl_result'];
  if (result != 'success')
   log('Plugin error: ' + result);
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
 ];
 for (var i=0; i<errorCallbacks.length; i++) {
  var err = errorCallbacks[i];
  window[err[0]] = function(arg) {
   log('Error: ' + err[1]);
  };
 }

 var deviceErrors = {
  '0': 'Ok',
  '10': 'App busy',
  '100': 'General',
  '200': 'USB',
  '201': 'SSL',
  '202': 'HTTP response',
  '203': 'HTTP digest',
  '204': 'HTTP redirect',
  '300': 'Task start',
  '400': 'Data actions',
  '500': 'Set account info',
  '501': 'Account info',
  '502': 'Download',
  '503': 'Install',
  '504': 'Contents',
  '505': 'Low battery',
  '506': 'Battery too hot',
  '800': 'Service from server',
 };
 window.pmcadl_ev_error_from_device = function(arg) {
  var result = arg['device_result_code'];
  var msg = deviceErrors[result];
  log('Device error: ' + (msg ? msg : result));
 };

 window.pmcaDownload = function(startUrl) {
  if (!state.plugin)
   return log('Error: Plugin not loaded');
  startTask(startUrl);
 }
 function startTask(url) {
  result(state.noResultText);
  log("Starting task");
  ajax(url, function(data) {
   state.taskKey = JSON.parse(data).id;
   log("Got task key");
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
  // We can't use https because Chrome doesn't like it...
  pluginMethod('pmcadl_request_sequence_start', {'trigger_url': 'http://' + location.hostname + '/camera/xpd/' + taskKey});
 }
 window.pmcadl_ev_progress = function(arg) {
  log('Progress: ' + arg['pr_text'] + ' ' + arg['pr_percent'] + '%');
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
