
$('.alert').on('close.bs.alert', function (e) {
  e.preventDefault();
  $(this).css('display', 'none')
  console.log('alert: dismiss');
  return true;
})

$('#fileupload').fileupload({
  dataType: 'text',
  autoUpload: false,
  singleFileUploads: false,
  maxFileSize: 1000000
})
.on('fileuploadadd', function (e, data) {
  console.log('Add:');
  var d = $(this).data('data');
  if (d){
    data.files = d.files.concat(data.files);
  }
  $(this).data('data', data);
  updateFileList(data);
})
.on('fileuploadsubmit', function(e, data) {
  console.log('Submit:');
  return true;
})
.on('fileuploadsend', function(e, data) {
  console.log('Send:');
  return true;
})

.on('fileuploaddone', function(e, data) {
  console.log('Done:');
  var xhr = data.jqXHR;

  var filename = "";
  var disp = xhr.getResponseHeader('Content-Disposition');
  if (disp && disp.indexOf('attachment') !== -1) {
    var re = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
    var match = re.exec(disp);
    if (match != null && match[1]) {
      filename = match[1].replace(/['"]/g, '');
    }
  }
  var type = xhr.getResponseHeader('Content-Type');
  var blob = new Blob([xhr.responseText], {type: type});
  var URL = window.URL || window.webkitURL;
  var downloadUrl = URL.createObjectURL(blob);

  if (filename) {
    // use HTML5 a[download] attribute to specify filename
    $('#download-result')
      .find('a').attr({'href': downloadUrl, 'download': filename})
      .find('span').text(filename)
      .end().end().show();

    // setTimeout(function () { URL.revokeObjectURL(downloadUrl); }, 100);

  } else {
    // window.location = downloadUrl;
  }
})

.on('fileuploadfail', function(e, data) {
  console.log('Fail:');
  var xhr = data.jqXHR;
  var resp = xhr.status + ': ' + xhr.statusText;
  if (xhr.getResponseHeader('Content-Type').endsWith('json')) {
    resp = JSON.parse(xhr.responseText)['error']
  }
  $('.alert-danger').css('display', 'block').find('span').last().text(resp);
})

.on('fileuploadalways', function(e, data) {
  console.log('Always:');
})
.on('click', 'button.start-button', function(e) {
  e.preventDefault();
  console.log('Start:');
  $('.alert').each(function() {
    $(this).css('display', 'none');
  });
  $('#download-result').css('display', 'none');
  var data = $('#fileupload').data('data');
  if (data) {
    $.each(data.files, function (index, file) { console.log(file.name) });
    // add button value to form data
    buttonData = [{name: 'datatype', value: $(this).val()}];
    data.formData = $('#fileupload').serializeArray().concat(buttonData);
    data.submit();
  }
})
.on('click', 'tbody.files button.remove', function(e) {
  e.preventDefault();
  var i = $('tbody.files tr').index($(this).closest('tr'));
  var data = $('#fileupload').data('data');
  data.files.splice(i, 1);
  updateFileList(data);
  if (data.files.length == 0) {
    $('#fileupload').removeData('data');
  }
})
.on('click', 'a.removeall', function(e) {
  e.preventDefault();
  var data = $('#fileupload').data('data');
  if (data) {
    data.files = [];
    updateFileList(data);
    $('#fileupload').removeData('data');
  }
})

function updateFileList(data) {
  var files = data.files;
  files.sort(function(a, b){return a.name > b.name ? 1 : -1});
  var rows = [];
  $.each(files, function (index, file) {
    var d = new Date(file.lastModified);
    rows.push($('<tr\>')
        .append(('<td>' + file.name + '</td>'))
        .append(('<td>' + d.toString().replace(/ \(.*/, '') + '</td>'))
        .append(('<td>' + file.size + '</td>'))
        .append(('<td style="text-align: center;"><button class="btn btn-xs btn-danger remove"><i class="glyphicon glyphicon-remove"></i></button></td>')));
  });
  $('tbody.files').find('tr').remove().end().append(rows);
}
