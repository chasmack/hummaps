/**
 * Created by Charlie on 11/27/2016.
 */

var $target = null;       // current a.map-info
var mapList = true;       // map list is displayed
var mapPage;              // current map mapPage
var shiftPressed;         // shift key is down
var ctrlPressed;          // ctrl key is down
var altPressed;           // alt key is down
var $loader = null;       // map view loader
var loaderTimeout = null; // setTimeout ID for delayed loader display
var disableKeyboardNavigation = false;   // need to disable arrow keys when dialog modal is open

// handler for window resize

$(window).resize(function (e) {

  // setup frame heights
  var win = $(window).height();
  var pad = 6;
  var nav = $('nav').outerHeight(false) + pad;
  var content = win - nav - pad;
  $('#content-frame').height(content).css({
    position: 'relative',
    top: nav,
    left: 0
  });
  $('#map-list').height(content).css('overflow-y', 'auto');
  $('#map-frame').height(content).css('overflow', 'hidden');
  if (!mapList) {
    zoomMap(0);
  }
}).trigger('resize');

// initialize the contents

if ($('div.flashed-messages').length) {

  // hide content if there are messages
  $('#map-list').hide();
  $('#map-frame').hide();

} else {

  // select the first map in the list
  $target = $('#map-list').find('.map-info:not(.disabled)').first();
  if ($target.length) {
    $target.addClass('active');
    mapPage = 1;
  } else {
    $target = null;
  }
  showMapList();
}

function showMapList() {

  if ($loader) {
    $loader.hide();
    $loader = null;
  }
  $('#map-frame').hide();
  $('#map-list').show();
  if ($target) {
    $target.focus();
  }
  mapList = true;
}

function showMap() {

  if ($target) {

    // remove any previous image and show the map view
    $('#map-frame img.map-image').remove();
    if (mapList) {
      $('#map-list').hide();
      $('#map-frame').show();
      mapList = false;
    }

    // get the current map image from the image list
    var $img = $target.find('.map-image-list .map-image').eq(mapPage - 1);
    if ($img.is('div')) {

      // display a loader if needed
      loaderTimeout = window.setTimeout(function() {
        console.log('timeout: ' + loaderTimeout);
        if (loaderTimeout) {
          $loader = $('#loader-frame').show();
          loaderTimeout = null;
        }
      }, 750);

      // replace div with an img element, this starts the download
      $img = $('<img class="map-image">').attr({
        src: $img.attr('data-src'),
        alt: $img.attr('data-alt')
      }).replaceAll($img)

      // callback to cancel loader and swap in the image
      $img.bind('load', function() {
        if (loaderTimeout) {
          window.clearTimeout(loaderTimeout);
          loaderTimeout = null;
        }
        if ($loader) {
          $loader.hide();
          $loader = null;
        }
        $('#map-frame').prepend($img.clone());
        zoomMap(0);
      });

    } else {

      // image should be ready to to display
      // cancel any loader and swap in image
      if (loaderTimeout) {
        window.clearTimeout(loaderTimeout);
        loaderTimeout = null;
      }
      if ($loader) {
        $loader.hide();
        $loader = null;
      }
      $('#map-frame').prepend($img.clone());
      zoomMap(0);
    }

    // update the map name label and scan link
    $('#map-name span').text($img.attr('alt'));
    var scan = $target.find('.scanfile-list .scanfile').eq(mapPage - 1);
    if (scan.length == 1) {
      $('<a>')
          .attr('href', scan.attr('data-href'))
          .text(scan.attr('data-alt'))
          .appendTo('#map-name span')
          .before('<br>');
    }
  }
}

function nextMap() {

  if ($target) {
    var $item = $target.parent().nextAll().children('.map-info:not(.disabled)').first();
    if ($item.length) {
      $target.removeClass('active');
      $target = $item.addClass('active');
      $target.focus();
      mapPage = 1;
      if (!mapList) {
        showMap();
      }
    }
  }
}

function prevMap(lastpage) {
  if ($target) {
    var $item = $target.parent().prevAll().children('.map-info:not(.disabled)').first();
    if ($item.length) {
      $target.removeClass('active');
      $target = $item.addClass('active');
      $target.focus();
      if (mapList) {
        mapPage = 1;
      } else {
        mapPage = lastpage ? $target.find('.map-image-list .map-image').length : 1;
        showMap();
      }
    }
  }
}

function nextPage() {
  if ($target) {
    $mapimages = $target.find('.map-image-list .map-image');
    if (mapPage < $mapimages.length) {
      mapPage += 1;
      showMap();
    } else {
      nextMap();
    }
  }
}

function prevPage() {
  if ($target) {
    if (mapPage == 1) {
      prevMap(true);
    } else {
      mapPage -= 1;
      showMap();
    }
  }
}

// nav buttons

$('#show-maps').click(function (e) {

  // toggle display of map list/image
  if (mapList) {
    showMap();
  } else {
    showMapList()
  }
  e.preventDefault();
});

$('#next').click(function (e) {

  // next map/page
  if (mapList) {
    nextMap();
  } else {
    nextPage();
  }
  e.preventDefault();
});

$('#prev').click(function (e) {

  // previous map/page
  if (mapList) {
    prevMap();
  } else {
    prevPage();
  }
  e.preventDefault();
});

// callbacks for map-item click and focus events

$('#map-list').on('click', 'a.map-info:not(.disabled)', function (e) {

  e.preventDefault();
  $target = $(this).focus();
  showMap();

}).on('focus', 'a.map-info:not(.disabled)', function (e) {

  if ($(this)[0] != $target[0]) {

    // update the currentMap
    $target.removeClass('active');
    $target = $(this).addClass('active');
    mapPage = 1;
  }
});

var mapZoomed = false;  // map image is zoomed
var zoomScale = 0.0;    // scale factor for map image

function zoomMap(increment, pageX, pageY) {

  // Scale the map image holding the origin fixed.
  // If increment is zero zoom image to minimum scale.
  // Mimimum scale is smaller of 100% height and 100% width.

  var zoomFactor = 1.5;     // change in zoom per zoom increment

  var $frame = $('#map-frame');
  var $img = $frame.find('img');

  if (increment < 0) {
    // negative increment to zoom out
    zoomScale /= zoomFactor * Math.abs(increment);
  } else {
    // positive increment to zoom in, zero means minimum scale
    zoomScale *= zoomFactor * increment;
  }

  // calculate min scale to fit entire image into the frame
  var natX = $img[0].naturalWidth;
  var natY = $img[0].naturalHeight;
  var minScale = Math.min($frame.width() / natX, $frame.height() / natY);

  if (!zoomScale || zoomScale < minScale) {
    zoomScale = minScale;
    mapZoomed = false;
  } else {
    mapZoomed = true;
  }

  // top-left corner of frame relative to the viewport+++++
  var offsetX = $frame.offset().left;
  var offsetY = $frame.offset().top;

  // origin relative frame corner, parameter is optional
  var originX = pageX ? (pageX - offsetX) : Math.round($frame.width() / 2);
  var originY = pageY ? (pageY - offsetY) : Math.round($frame.height() / 2);

  // image size
  var imgX = $img.outerWidth();
  var imgY = $img.outerHeight();

  // top-left corner frame relative to the image
  var scrollX = $frame.scrollLeft();
  var scrollY = $frame.scrollTop();

  // zoom origin relative to the top-left corner of the image
  // top-left corner is (0.0, 0.0), bottom-right corner is (1.0, 1.0)
  var relX = (originX + scrollX) / imgX;
  var relY = (originY + scrollY) / imgY;

  // scaled image size
  imgX = Math.round(zoomScale * natX);
  imgY = Math.round(zoomScale * natY);

  // new scroll offsets
  scrollX = Math.round(imgX * relX - originX);
  scrollY = Math.round(imgY * relY - originY);

  // set new image size and frame scroll
  $img.css('width', imgX).css('height', imgY);
  $frame.scrollLeft(scrollX).scrollTop(scrollY);
}

function findBootstrapEnv() {
  var envs = ['xs', 'sm', 'md', 'lg'];

  var $el = $('<div>');
  $el.appendTo($('body'));

  for (var i = envs.length - 1; i >= 0; i--) {
    var env = envs[i];

    $el.addClass('hidden-' + env);
    if ($el.is(':hidden')) {
      $el.remove();
      return env;
    }
  }
}

// keypress related stuff

var arrowLockout = false;     // prevent keydown repeat for arrows

$(window).keydown(function (e) {

  if (disableKeyboardNavigation) {
    return;
  }

  // console.log('keydown: ' + e.which);
  switch (e.which) {
    case 16:  // shift
      shiftPressed = true;
      break;
    case 17:  // ctrl
      ctrlPressed = true;
      break;
    case 18:  // alt
      altPressed = true;
      break;
    case 27:  // esc
      showMapList();
      break;
    case 37:  // left arrow
      if (!mapList) {
        prevPage();
        arrowLockout = true;
        e.preventDefault();
      }
      break;
    case 38:  // up arrow
      prevMap();
      arrowLockout = true;
      e.preventDefault();
      break;
    case 39:  // right arrow
      if (!mapList) {
        nextPage();
        arrowLockout = true;
        e.preventDefault();
      }
      break;
    case 40:  // down arrow
      nextMap();
      arrowLockout = true;
      e.preventDefault();
      break;
  }

}).keyup(function (e) {

  // console.log('keyup: ' + e.which);
  switch (e.which) {
    case 16:  // shift
      shiftPressed = false;
      break;
    case 17:  // ctrl
      ctrlPressed = false;
      break;
    case 18:  // alt
      altPressed = false;
      break;
    case 37:  // left arrow
    case 38:  // up arrow
    case 39:  // right arrow
    case 40:  // down arrow
      arrowLockout = false;
      break;
  }

}).keypress(function(e) {

  // console.log('keypress: ' + e.which);
  switch (e.which) {
    case '+'.charCodeAt():
    case '-'.charCodeAt():
      if (!mapList) {
        // if mouse pointer is in the map frame use pointer as zoom origin
        var $frame = $('#map-frame');
        var left = $frame.offset().left;
        var top = $frame.offset().top;
        var right = left + $frame.width();
        var bottom = top + $frame.height();
        var zf = e.which == '+'.charCodeAt() ? +1 : -1;
        if (mouseX > left && mouseY < right && mouseY > top && mouseY < bottom) {
          zoomMap(zf, mouseX, mouseY);
        } else {
          zoomMap(zf);
        }
      }
      break;
    case 32:  // space bar
      if (!mapList) {
        // spacebar in map view will zoom to minimum
        zoomMap(0);
      }
      break;
  }
});

// mouse related stuff

var mouseDown;        // mouse button is down
var mouseX;           // last mouse x while down
var mouseY;           // last mouse y while down
var mouseMove;        // accumulate absolute X/Y mouse movements while mouse down

$('#map-frame').on('mousedown', 'img', function (e) {

  // start monitoring mouse movements
  // console.log('mousedown: ' + e.which);
  if (e.which == 1) {

    mouseX = e.pageX;
    mouseY = e.pageY;
    mouseDown = true;
    mouseMove = 0;
  }
  e.preventDefault();
});

$('#map-frame').on('mouseup', 'img', function (e) {

  // zoom if accumulated mouse movements are small
  // console.log('mouseup: ' + e.which);
  // if (mouseDown && mouseMove < 10) {
  //   if (shiftPressed) {
  //     zoomMap(-1, e.pageX, e.pageY);  // zoom out
  //   } else {
  //     zoomMap(+1, e.pageX, e.pageY);  // zoom in
  //   }
  // }
  mouseDown = false;
  e.preventDefault();
});

$('#map-frame').on('mousemove', 'img', function (e) {

  var accel = 2;
  var dx, dy;
  var dx = mouseX - e.pageX;
  var dy = mouseY - e.pageY;
  if (mapZoomed && mouseDown) {

    // scroll the map image
    dx = mouseX - e.pageX;
    dy = mouseY - e.pageY;
    $('#map-frame').scrollLeft($('#map-frame').scrollLeft() + dx * accel);
    $('#map-frame').scrollTop($('#map-frame').scrollTop() + dy * accel);
  }
  mouseX = e.pageX;
  mouseY = e.pageY;
  mouseMove += Math.abs(dx) + Math.abs(dy);
  e.preventDefault();
});

$('#map-frame').on('mouseleave', 'img', function (e) {

  mouseDown = false;
  e.preventDefault();
});

$('#map-frame').on('mousewheel', 'img', function (e) {

  if (e.deltaY < 0) {
    zoomMap(-1, e.pageX, e.pageY);
  } else {
    zoomMap(+1, e.pageX, e.pageY);
  }
  e.preventDefault();
});
