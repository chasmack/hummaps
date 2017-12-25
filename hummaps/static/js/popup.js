/**
* Created by Charlie on 12/23/2017.
*/

$('#search-dialog')
    // Disable arrow key navigation when modal is open.
    .on('shown.bs.modal', function(e) {
      disableKeyboardNavigation = true;
      $('#input-section').focus();

    })
    // Re-enable arrow key navigation annd hide any popovers.
    .on('hide.bs.modal', function(e) {
      disableKeyboardNavigation = false;
      $('div.help-popover').each(function(i) {
        $(this).popover('hide');
      });
    })
    // Enter in main inputs to circulate focus.
    .on('keypress', '.dialog-circulate', function(e) {
      if (e.key == 'Enter') {
        var $circ = $('input.dialog-circulate');
        var i = $circ.index(this) + 1;
        if (i < $circ.length) {
          $circ.eq(i).focus();
          e.preventDefault();
        }
      }
    })
    // Toggle popover visibility making sure other popovers are hidden.
    .on('click', '.help-popover', function(e) {
      var target = $(this);
      $('#search-dialog').find('.help-popover').not(target).each(function(i) {
        $(this).popover('hide');
      });
      target.popover('toggle');
    });

// Initialize the BS plugin for the help popovers.
$('[data-toggle="popover"]').popover();

// Setup the inputs and help popovers
$('#input-section')
    .attr({
      placeholder: 'eg. s22',
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate')
    .closest('.form-group').find('.help-popover').popover({
      trigger: 'manual',
      container: 'body',
      html: true,
      content:
        '<p>Type one or more section numbers separated by space -</p>' +
        '<p style="padding-left: .5em"><strong>S12</strong></p>' +
        '<p style="padding-left: .5em"><strong>S11 S12 S13 S14</strong></p>' +
        '<p>Subsections can be added in front of the section numbers -</p>' +
        '<p style="padding-left: .5em"><strong>S/2 S12</strong></p>' +
        '<p style="padding-left: .5em"><strong>NE/4 SW/4 S16</strong></p>'
    });

$('#input-township')
    .attr({
      placeholder: 'eg. 5n',
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate')
    .closest('.form-group').find('.help-popover').popover({
      trigger: 'manual',
      container: 'body',
      html: true,
      content:
        '<p>Type a single township number followed by "N" or "S" - <strong>T6N</strong></p>' +
        '<p>The "T" prefix is optional - <strong>6N</strong></p>'
    });

$('#input-range')
    .attr({
      placeholder: 'eg. 1w',
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate')
    .closest('.form-group').find('.help-popover').popover({
      trigger: 'manual',
      container: 'body',
      html: true,
      content:
        '<p>Type a single range number followed by "E" or "W" - <strong>R4E</strong></p>' +
        '<p>The "R" prefix is optional - <strong>4E</strong></p>'
    });

$('#input-recdate')
    .attr({
      placeholder: 'eg. 12/2017',
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate')
    .closest('.form-group').find('.help-popover').popover({
      trigger: 'manual',
      container: 'body',
      html: true,
      content:
        '<p>Type a year, month or day like -</p>' +
        '<p style="padding-left: .5em"><strong>2017</strong> or <strong>6/2017</strong> or <strong>6/22/2017</strong></p>' +
        '<p>Use an optional second date in the "To" field to specify a date range.</p>'
    });

 $('#input-recdate-to')
    .attr({
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate');

$('#input-surveyor')
    .attr({
      placeholder: 'type a name or number...',
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate typeahead')
    .one('input', function(e) {
      // Lazy initialization of the surveyor typeahead.
      var input = $(this);
      $.get('/', { req: 'surveyors' }, function(data) {
        // console.log('init surveyor typeahead: ' + data.length + ' items');
        input.typeahead({
          source: data,
          appendTo: '#search-dialog',
          minLength: 2,
          items: 10
        });
      }, 'json');
    })
    .closest('.form-group').find('.help-popover').popover({
      trigger: 'manual',
      container: 'body',
      html: true,
      content:
        '<p>Type a few characters from a name or LS/RCE number and select a surveyor from the list.</p>'
    }) ;

$('#input-client')
    .attr({
      placeholder: 'type a client or subdivision...',
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate')
    .closest('.form-group').find('.help-popover').popover({
      trigger: 'manual',
      container: 'body',
      html: true,
      content:
        '<p>Type a client or subdivision name. This field supports a limited set of ' +
        '<a href="https://www.postgresql.org/docs/9.4/static/functions-matching.html#FUNCTIONS-POSIX-REGEXP" target="_blank">' +
        'regular expressions.</a></p>'
    });

$('#input-description')
    .attr({
      placeholder: 'type a word or phrase...',
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate')
    .closest('.form-group').find('.help-popover').popover({
      trigger: 'manual',
      container: 'body',
      html: true,
      content:
        '<p>Type a word or phrase from the map description. This field supports a limited set of ' +
        '<a href="https://www.postgresql.org/docs/9.4/static/functions-matching.html#FUNCTIONS-POSIX-REGEXP" target="_blank">' +
        'regular expressions.</a></p>'
    });

$('#input-maps')
    .attr({
      placeholder: 'eg. 68rs136 26pm151',
      autocomplete: "off",
      spellcheck: "false"
    })
    .addClass('dialog-circulate')
    .closest('.form-group').find('.help-popover').popover({
      trigger: 'manual',
      container: 'body',
      html: true,
      content:
        '<p>Type one or more map names specifying a book and page, parcel map number or tract number -</p>' +
        '<p style="padding-left: .5em"><strong>68rs136</strong></p>' +
        '<p style="padding-left: .5em"><strong>pm2938</strong></p>' +
        '<p style="padding-left: .5em"><strong>tr445</strong></p>' +
        '<p>Separate multiple maps with space -</p>' +
        '<p style="padding-left: .5em"><strong>68rs136 26pm151</strong></p>' +
        '<p>DO NOT include any space within individual map names.</p>'
    });

// Input validation
jQuery.fn.extend({
  trimValue: function() {
    var trimmed = $.trim(this.val());
    // update input if all space
    if (trimmed.length == 0)
      this.val(trimmed);
    return trimmed;
  },
  validationState: function(state) {
    return this.each(function() {
      var fg = $(this).closest('.form-group')[0];
      fg.className = fg.className
          .split(/\s+/).filter(function(a) { return a.indexOf('has-') != 0 })
          .concat(state).join(' ').trim();
    });
  },
  hasError: function() {
    var has_error = false;
    this.each(function() {
      if ($(this).closest('.form-group').hasClass('has-error')) {
        has_error = true;
        return false;
      }
    });
    return has_error
  },
});

function validateSection(input) {
  console.log('validateSection()');
  var val = input.trimValue();
  var error_msg = '';

  if (val.length > 0) {

    // Check for one or more section specs consisting of an optional
    // subsection followed by an "S" and one or two digits. Multiple
    // section specs are separated by space or a comma and optional space.
    //
    // Example: SW/4 SW/4 S1, E/2 S2, N/2 N/2 S12
    //
    // Valid subsections are -
    //  (1) [NS][EW]/4\s+[NS][EW]/4   eg. NW/4 SE/4 (40 ac)
    //  (2) [NSEW]/2\s+[NS][EW]/4     eg. N/2 SE/4 (80 ac)
    //  (3) [NS]/2\s+[NS]/2           eg. N/2 S/2 (160 ac)
    //  (4) [EW]/2\s+[EW]/2           eg. E/2 W/2 (160 ac)
    //  (5) [NS][EW]/4                eg. NE/4 (160 ac)
    //  (6) [NSEW]/2                  eg. E/2 (320 ac)
    //  (7) 1/1                       Shorthand for the full section (640 ac)
    //
    // Expressions like E/2 N/2 are not valid. Use NE/4 instead.
    // Expressions like NW/4 E/2 are not valid. You probably want W/2 NE/4.

    var pat = '' +
      '(([NS][EW]/4|[NSEW]/2)\\s+)?[NS][EW]/4\\s+' +    // (1), (2) & (5)
      '|([NS]/2\\s+)?[NS]/2\\s+' +                      // (3) & part of (6)
      '|([EW]/2\\s+)?[EW]/2\\s+' +                      // (4) & part of (6)
      '|1/1\\s+';                                       // (7)

    pat = '^(' + pat + ')?S\\d{1,2}$';                  // a section
    var re = new RegExp(pat, 'i');

    // Split line into individual sections.
    var parts = val.split(/(S\d+)(,\s*|\s+|(?!,)$)/i);
    if (parts.length == 1) {
      // Doesn't look like a section.
      error_msg = 'Bad section: ' + val;

    } else {
      // For each section there are three parts: subsection, section and separator.
      // A terminal separator generates an empty final part. Dispose of it.
      parts.pop();
      for (var i = 0; i < parts.length; i += 3) {
        var sec = parts[i] + parts[i + 1];

        // The final separator should be empty.
        if (i + 3 == parts.length) {
          sec += parts[i + 2];
        }
        // Check the section pattern.
        if (!re.test(sec)) {
          error_msg = 'Bad section: ' + sec;
          break;
        }
        // Check section numbers.
        var n = parseInt(sec.match(/\d+$/)[0]);
        if (n < 1 || n > 36) {
          error_msg = 'Bad section: ' + sec;
          break;
        }
      }
    }
  }
  if (error_msg) {
    input.validationState('has-error');
    $('#help-block').attr('class', 'text-danger').text(error_msg);
  } else if (val.length > 0) {
    input.validationState('has-success');
    $('#help-block').removeClass().text('');
  } else {
    input.validationState();
    $('#help-block').removeClass().text('');
  }
}

$('#input-section')
  .on('blur', function(e) {validateSection($(this))})
  .on('keyup', function(e){
    var input = $(this);
    if (input.hasError())
      setTimeout(validateSection, 200, input);
  });

function validateTownship(input) {
  console.log('validateTownship()');
  var val = input.trimValue();
  var error_msg = '';

  if (val.length > 0) {
    var re = new RegExp('^T?\\d{1,2}[NS]$', 'i');
    if (!re.test(val)) {
      error_msg = 'Bad township: ' + val;
    }
  }
  if (error_msg) {
    input.validationState('has-error');
    $('#help-block').attr('class', 'text-danger').text(error_msg);
  } else if (val.length > 0) {
    input.validationState('has-success');
    $('#help-block').removeClass().text('');
  } else {
    input.validationState();
    $('#help-block').removeClass().text('');
  }
}

$('#input-township')
  .on('blur', function(e) {validateTownship($(this))})
  .on('keyup', function(e){
    var input = $(this);
    if (input.hasError())
      setTimeout(validateTownship, 200, input);
  });

function validateRange(input) {
  console.log('validateRange()');
  var val = input.trimValue();
  var error_msg = '';

  if (val.length > 0) {
    var re = new RegExp('^R?\\d{1,2}[EW]$', 'i');
    if (!re.test(val)) {
      error_msg = 'Bad range: ' + val;
    }
  }
  if (error_msg) {
    input.validationState('has-error');
    $('#help-block').attr('class', 'text-danger').text(error_msg);
  } else if (val.length > 0) {
    input.validationState('has-success');
    $('#help-block').removeClass().text('');
  } else {
    input.validationState();
    $('#help-block').removeClass().text('');
  }
}

$('#input-range')
  .on('blur', function(e) {validateRange($(this))})
  .on('keyup', function(e){
    var input = $(this);
    if (input.hasError())
      setTimeout(validateRange, 200, input);
  });

function validateRecdate(input) {
  console.log('validateRecdate()');
  var val = input.trimValue();
  var error_msg = '';

  if (val.length > 0) {
    var re = new RegExp('^((\\d{1,2}/)?\\d{1,2}/)?\\d{4}$');
    if (!re.test(val)) {
      error_msg = 'Bad date: ' + val;
    } else {
      var parts = val.split('/');
      var year, month, day;
      switch (parts.length) {
        case 3:
          day = parseInt(parts[1]);
          month = parseInt(parts[0]);
          year = parseInt(parts[2]);
          break;
        case 2:
          month = parseInt(parts[0]);
          year = parseInt(parts[1]);
          break;
        case 1:
          year = parseInt(parts[0]);
          break;
      }
      if (year < 1800 || year > 2100) {
        error_msg = 'Bad year: ' + val;

      } else if (parts.length == 2 && (month < 1 || month > 12)) {
        error_msg = 'Bad month: ' + val;

      } else if (parts.length == 3) {
        switch (month) {
          case 1:
          case 3:
          case 5:
          case 7:
          case 8:
          case 10:
          case 12:
            if (day == 0 || day > 31)
              error_msg = 'Bad day: ' + val;
            break;

          case 4:
          case 6:
          case 9:
          case 11:
            if (day == 0 || day > 30)
              error_msg = 'Bad day: ' + val;
            break;

          case 2:
            if ((year % 4 == 0) && (year % 100 != 0) || (year % 400 == 0)) {
              if (day == 0 || day > 29)   // leap year
                error_msg = 'Bad day: ' + val;
            } else {
              if (day == 0 || day > 28)
                error_msg = 'Bad day: ' + val;
            }
            break;
        }
      }
    }
  }
  // recdate and recdate-to inputs share a form-group so
  // errors have to be applied to the input's div and label.
  if (error_msg) {
    input.parent().removeClass('has-success').addClass('has-error')
      .prev().removeClass('text-success').addClass('text-danger');
    $('#help-block').attr('class', 'text-danger').text(error_msg);
  } else if (val.length > 0) {
    input.parent().removeClass('has-error').addClass('has-success')
      .prev().removeClass('text-danger').addClass('text-success');
    $('#help-block').removeClass().text('');
  } else {
    input.parent().removeClass('has-success has-error')
      .prev().removeClass('text-success text-danger');
    $('#help-block').removeClass().text('');
  }
}

$('#input-recdate')
  .on('blur', function(e) {validateRecdate($(this))})
  .on('keyup', function(e){
    var input = $(this);
    if (input.parent().hasClass('has-error'))
      setTimeout(validateRecdate, 200, input);
  });

$('#input-recdate-to')
  .on('blur', function(e) {validateRecdate($(this))})
  .on('keyup', function(e){
    var input = $(this);
    if (input.parent().hasClass('has-error'))
      setTimeout(validateRecdate, 200, input);
  });

$('#input-surveyor').on('blur', function(e) {
  console.log('validateSurveyor()');
  var input = $(this);
  var val = input.trimValue();

  // Not much we can check.

  if (val.length > 0) {
    input.validationState('has-success');
  } else {
    input.validationState();
  }
});

$('#input-client').on('blur', function(e) {
  console.log('validateClient()');
  var input = $(this);
  var val = input.trimValue();

  // Not much we can check.

  if (val.length > 0) {
    input.validationState('has-success');
  } else {
    input.validationState();
  }
});

$('#input-description').on('blur', function(e) {
  console.log('validateDescription()');
  var input = $(this);
  var val = input.trimValue();

  // Not much we can check.

  if (val.length > 0) {
    input.validationState('has-success');
  } else {
    input.validationState();
  }
});

function validateMaps(input) {
  console.log('validateMaps()');
  var val = input.trimValue();
  var error_msg = '';

  if (val.length > 0) {

    // Get a list of the valid map types
    var maptypes = [];
    $('#search-dialog').find('[name^="maptype"]').each(function (i) {
      $.merge(maptypes, $(this).parent().text().match(/\(.*\)/)[0].match(/\w{2}/g));
    });
    maptypes = maptypes.concat('MAPS', 'M', 'SM', 'S').join('|');

    // One or more maps separated by space
    var pat = '^((\\d{1,3}(' + maptypes + ')\\d{1,3}|(PM|TR)\\d{1,4})(\\s+|$))+$';
    var re = new RegExp(pat, 'i');
    if (!re.test(val)) {
      var m = val.split(/\s+/);
      var bad = [];
      for (var i = 0; i < m.length; i++) {
        if (!re.test(m[i])) {
          bad.push(m[i]);
        }
      }
      error_msg = 'Bad map: ' + bad.join(' ');
    }
  }
  if (error_msg) {
    input.validationState('has-error');
    $('#help-block').attr('class', 'text-danger').text(error_msg);
  } else if (val.length > 0) {
    input.validationState('has-success');
    $('#help-block').removeClass().text('');
  } else {
    input.validationState();
    $('#help-block').removeClass().text('');
  }
}

$('#input-maps')
    .on('blur', function(e) {validateMaps($(this))})
    .on('keypress', function(e) {
      var input = $(this);
      if (e.key == 'Enter') {
        e.preventDefault();
        validateMaps(input);
        if (!input.hasError()) {
          $('#search-submit').click();
        }
      }
    })
    .on('keyup', function(e) {
      var input = $(this);
      if (e.key != 'Enter' && input.hasError())
        setTimeout(validateMaps, 200, input);
    });

// Warn if there are no map types selected
function validateMaptypes() {
  console.log('validateMaptypes()');
  var maptypes = $('input[name^="maptype"]');
  if (maptypes.filter(':checked').length == 0) {
    maptypes.validationState('has-error');
    $('#help-block').attr('class', 'text-danger').text('No map types selected.');
  } else {
    maptypes.validationState();
    $('#help-block').removeClass('text-danger').text('');
  }
}

$('#search-dialog').on('change', 'input[name^="maptype"]', validateMaptypes);

// Run through the validators on startup
$('#search-dialog').find('input').not('[name^="maptype"]').blur()
    .end().filter('[name^="maptype"]').first().change();

// Combine form data into a query string, hide dialog and submit search.
$('#search-submit').on('click', function (e) {

  // Manually submit form if appropriate.
  e.preventDefault()

  var $dialog = $('#search-dialog');
  var val = {};
  // Trim space from input and collect values into an object.
  $dialog.find('input').each(function(i) {
    var input = $(this);
    var trimmed = input.val().trim();
    input.val(trimmed);
    val[this.name] = trimmed;
  });

  var terms = [];
  if (val['township'].length > 0 && val['range'].length > 0) {
    terms.push(val['township'], val['range']);
    if (val['section'].length > 0) {
      terms.unshift(val['section']);
    }
  }

  if (val['recdate'].length > 0) {
    if (val['recdate-to'].length > 0) {
      terms.push('date="' + val['recdate'] + ' ' + val['recdate-to'] + '"');
    } else {
      terms.push('date="' + val['recdate'] + '"');
    }
  }

  if (val['surveyor'].length > 0) {
    // Strip off the LS/RCE number before adding to the query string.
    terms.push('by="' + val['surveyor'].match(/.*?(?=\s*\()/)[0] + '"');
  }

  if (val['client'].length > 0) {
    terms.push('for="' + val['client'] + '"');
  }

  if (val['description'].length > 0) {
    terms.push('desc="' + val['description'] + '"');
  }

  if (terms.length > 0) {
    var $maptypes = $('input[name^="maptype"]');
    var $selected = $maptypes.filter(':checked');
    if ($selected.length < $maptypes.length && $selected.length > 0) {
      // Only need maptypes if something is not selected and at least
      // one maptype is selected. The case where no maptypes are selected
      // makes no sense so we do nothing to qualify maptypes.
      var types = [];
      $selected.each(function (i) {
        // Maptype abbreviations are two alpha chars inside parens.
        // Multiple maptypes are separate by a comma and space.
        $.merge(types, $(this).parent().text().match(/\(.*\)/)[0].match(/\w{2}/g));
      });
      terms.push('type=' + types.join('|').toLowerCase());
    }
  }

  if (val['maps'].length > 0) {
    terms.push(val['maps']);
  }

  $dialog.modal('hide');

  if (terms.length > 0) {
    var query = terms.join(' ');
    $('#search-query').val(query);
    $('#search-dialog form').attr('action', '/?q=' + encodeURIComponent(query)).submit();
  }
});
