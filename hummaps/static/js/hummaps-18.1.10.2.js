/**
 * Created by Charlie on 11/27/2016.
 */

var mapList = true;       // map list is displayed
var currentMap;           // current map-info
var mapPage;              // current map page
var mapImage;             // current DOM map image
var frameSize;            // map frame size
var imageSize;            // natural size of the map image
var imageScaleMin;        // minimum scale to fit map into the map frame
var imageScale;           // scale of the map image
var imageOffset;          // origin of the map image relative to the map frame
var zoomStep = 1.35;      // factor to change zoom scale per step
var resizeLockout;        // prevent resize of frame
var loader = null;        // map view loader
var loaderTimeout = null; // setTimeout ID for delayed loader display

$(function() {

  // Initialize content frame size.
  resizeLockout = false;
  updateFrameSize();

  if ($('div.flashed-messages').length) {

    // Hide content if there are messages.
    $('#map-list').hide();
    $('#map-frame').hide();

  } else {

    // Select the first map and displat the map list.
    currentMap = $('#map-list').find('.map-info:not(.disabled)').first();
    if (currentMap.length == 1) {
      currentMap.addClass('active');
      mapPage = 1;
    } else {
      currentMap = null;
    }
    showMapList();
  }
});

// Handlers for window resize, map-info click and focus.

function updateFrameSize() {

  // Setup frame heights.
  var win = $(window).height();
  var pad = 6;
  var nav = $('nav').outerHeight(false) + pad;
  var content = win - nav - pad;
  var frame = $('#content-frame').height(content).css({
    position: 'relative',
    top: nav,
    left: 0
  });
  frameSize = {x: frame.width(), y: frame.height()};

  $('#map-list').height(content).css('overflow-y', 'auto');
  $('#map-frame').height(content).css('overflow', 'hidden');
}

$(window).on('resize', function (e) {

  if (resizeLockout) return;

  updateFrameSize();
  if (!mapList) {
    showMap();
  }
});

$('#map-list').on('click', 'a.map-info:not(.disabled)', function (e) {

  e.preventDefault();
  currentMap = $(this).focus();
  showMap();

}).on('focus', 'a.map-info:not(.disabled)', function (e) {

  if (this != currentMap[0]) {

    // update the currentMap
    currentMap.removeClass('active');
    currentMap = $(this).addClass('active');
    mapPage = 1;
  }
});

// Navbar collapse handlers.

$('#searchbar').collapse({
  toggle: false
});

$('nav').on('click', '.navbar-toggle', function(e) {
  $('#searchbar').collapse('toggle');
});

$('div.navbar-collapse').on('click', 'a', function(e) {
  $('#searchbar').collapse('hide');
});

$('div.navbar-collapse').on('submit', 'form', function(e) {
  $('#searchbar').collapse('hide');
});

$('div.navbar-collapse').on('show.bs.collapse', function(e) {
  resizeLockout = true;
});

$('div.navbar-collapse').on('hidden.bs.collapse', function(e) {
  resizeLockout = false;
});

// Handlers for nav buttons.

$('#search-dialog').modal({
  show: false

}).on('hidden.bs.modal', function (e) {
  window.setTimeout(function() {
    resizeLockout = false;
  }, 500);
});

$('#show-dialog').on('click', function (e) {
  $('#search-dialog').modal('toggle');
  resizeLockout = true;
});

$('#show-maps').on('click', function (e) {
  if (mapList) {
    showMap();
  } else {
    showMapList()
  }
});

$('#next').on('click', function (e) {
  if (mapList) {
    nextMap();
  } else {
    nextPage();
  }
});

$('#prev').on('click', function (e) {
  if (mapList) {
    prevMap();
  } else {
    prevPage();
  }
});

// Map list navigation.

function nextPage() {
  if (currentMap) {
    $mapimages = currentMap.find('.map-image-list .map-image');
    if (mapPage < $mapimages.length) {
      mapPage += 1;
      showMap();
    } else {
      nextMap();
    }
  }
}

function prevPage() {
  if (currentMap) {
    if (mapPage == 1) {
      prevMap(true);
    } else {
      mapPage -= 1;
      showMap();
    }
  }
}

function nextMap() {
  if (currentMap) {
    var $item = currentMap.parent().nextAll().children('.map-info:not(.disabled)').first();
    if ($item.length) {
      currentMap.removeClass('active');
      currentMap = $item.addClass('active');
      currentMap.focus();
      mapPage = 1;
      if (!mapList) {
        showMap();
      }
    }
  }
}

function prevMap(lastpage) {
  if (currentMap) {
    var $item = currentMap.parent().prevAll().children('.map-info:not(.disabled)').first();
    if ($item.length) {
      currentMap.removeClass('active');
      currentMap = $item.addClass('active');
      currentMap.focus();
      if (mapList) {
        mapPage = 1;
      } else {
        mapPage = lastpage ? currentMap.find('.map-image-list .map-image').length : 1;
        showMap();
      }
    }
  }
}

// Display the map list.

function showMapList() {
  if (loader) {
    loader.hide();
    loader = null;
  }
  $('#map-frame').hide();
  $('#map-list').show();
  if (currentMap) {
    currentMap.focus();
  }
  mapList = true;
}

// Display the map view.

function showMap() {
  if (currentMap) {

    // Remove any existing map canvas.
    $('#map-canvas').remove();

    if (mapList) {
      $('#map-list').hide();
      mapList = false;
    }
    $('#map-frame').show();

    // Get the current map image from the image list.
    var img = currentMap.find('.map-image-list .map-image').eq(mapPage - 1);
    if (img.is('div')) {

      // display a loader if needed
      loaderTimeout = window.setTimeout(function() {
        // console.log('timeout: ' + loaderTimeout);
        if (loaderTimeout) {
          loader = $('#loader-frame').show();
          loaderTimeout = null;
        }
      }, 750);

      // Replace div with an img element, this starts the download.
      img = $('<img>').attr({
        class: 'map-image',
        src: img.attr('data-src'),
        alt: img.attr('data-alt')
      }).replaceAll(img);

      // Callback to draw the image and cancel the loader.
      img.on('load', function() {
        if (loaderTimeout) {
          window.clearTimeout(loaderTimeout);
          loaderTimeout = null;
        }
        if (loader) {
          loader.hide();
          loader = null;
        }
        showMapCanvas(img);
      });

    } else {

      // Image should be ready to to display.
      // Cancel any loader and draw the image.
      if (loaderTimeout) {
        window.clearTimeout(loaderTimeout);
        loaderTimeout = null;
      }
      if (loader) {
        loader.hide();
        loader = null;
      }
      showMapCanvas(img);
    }

    // Update the map name label and scan link.
    $('#map-name').find('span').text(img.attr('alt'));
    var scan = currentMap.find('.scanfile-list .scanfile').eq(mapPage - 1);
    if (scan.length == 1) {
      $('<a>')
        .attr('href', scan.attr('data-href'))
        .text(scan.attr('data-alt'))
        .appendTo('#map-name span')
        .before('<br>');
    }
  }
}

function showMapCanvas(img) {

  mapImage = img[0];
  imageSize = {x: mapImage.naturalWidth, y: mapImage.naturalHeight};
  imageScaleMin = Math.min(frameSize.x / imageSize.x, frameSize.y / imageSize.y);
  imageScale = imageScaleMin;
  imageOffset = {x: 0, y: 0};

  // Add a new canvas.
  var canvas = document.createElement('canvas');
  canvas.width = frameSize.x;
  canvas.height = frameSize.y;
  canvas.id = 'map-canvas';
  $('#map-frame').prepend(canvas);

  drawMapImage();
}

function drawMapImage() {

  var ctx = document.getElementById('map-canvas').getContext('2d');
  ctx.clearRect(0, 0, frameSize.x, frameSize.y);
  ctx.save();
  ctx.transform(imageScale, 0, 0, imageScale, imageOffset.x, imageOffset.y);
  ctx.drawImage(mapImage, 0, 0);
  ctx.restore();
}

function panMapImage(dx, dy) {

  // Clamp new offset to frame boundaries.
  imageOffset.x = Math.round(Math.max(dx, frameSize.x - imageSize.x * imageScale));
  imageOffset.y = Math.round(Math.max(dy, frameSize.y - imageSize.y * imageScale));
  if (imageOffset.x > 0) imageOffset.x = 0;
  if (imageOffset.y > 0) imageOffset.y = 0;

  drawMapImage();
}

function zoomMapImage(scale, pageX, pageY) {

  if (imageScale == imageScaleMin && scale <= imageScaleMin) return;

  var initialScale = imageScale;
  imageScale = (scale > imageScaleMin) ? scale : imageScaleMin;

  // Zoom origin relative to the frame.
  var frame = $('#map-frame');
  var originX, originY;
  if (pageX && pageY) {
    originX = pageX - frame.offset().left;
    originY = pageY - frame.offset().top;
  } else {
    originX = frame.width() / 2;
    originY = frame.height() / 2;
  }

  // Set new offset and clamp to frame boundaries.
  imageOffset.x = imageScale / initialScale * (imageOffset.x - originX) + originX;
  imageOffset.y = imageScale / initialScale * (imageOffset.y - originY) + originY;
  imageOffset.y = Math.round(Math.max(imageOffset.y, frameSize.y - imageSize.y * imageScale));
  imageOffset.x = Math.round(Math.max(imageOffset.x, frameSize.x - imageSize.x * imageScale));
  imageOffset.x = Math.round(Math.max(imageOffset.x, frameSize.x - imageSize.x * imageScale));
  if (imageOffset.x > 0) imageOffset.x = 0;
  if (imageOffset.y > 0) imageOffset.y = 0;

  drawMapImage();
}

// Keypress related stuff.

// Stop query and dialog keyboard events from propagating up.
$('#search-query').add('#search-dialog')
  .on('keydown keyup keypress', function(e) {
    e.stopPropagation();
})

$(window).on('keydown', function (e) {

  var key = e.key;
  if (key.indexOf('Arrow') == 0) {
    key = key.substr(5);
  } else if (key.indexOf('Esc') == 0) {
    key = 'Esc';
  }
  // console.log('keydown: ' + e.key + ' (' + key + ')');
  switch (key) {
    case 'Esc':
      showMapList();
      break;
    case 'Left':
      if (!mapList) {
        prevPage();
        e.preventDefault();
      }
      break;
    case 'Right':
      if (!mapList) {
        nextPage();
        e.preventDefault();
      }
      break;
    case 'Up':
      prevMap();
      e.preventDefault();
      break;
    case 'Down':
      nextMap();
      e.preventDefault();
      break;
  }

}).on('keypress', function(e) {

  var key = e.char || e.key;
  // console.log('keypress: "' + key + '"');
  if (!mapList) {
    switch (key) {
      case '+':
        zoomMapImage(imageScale * zoomStep);
        break;
      case '-':
        zoomMapImage(imageScale / zoomStep);
        break;
      case ' ':
        // space zooms to minimum
        zoomMapImage(0);
        break;
    }
  }
});

// Mouse and touch related stuff.

$('#map-frame').on('mousewheel', function (e) {

  // console.log('mousewheel');
  if (e.deltaY > 0) {
    zoomMapImage(imageScale * zoomStep, e.pageX, e.pageY);
  } else {
    zoomMapImage(imageScale / zoomStep, e.pageX, e.pageY);
  }
  e.preventDefault();
  e.stopPropagation();
});

var ham = new Hammer.Manager($('#map-frame').get(0), {
  // domEvents: true
});

ham.add( new Hammer.Pan({ }) );
ham.add( new Hammer.Pinch({ }) );

// ham.add( new Hammer.Tap({ event: 'singletap' }) );
// ham.add( new Hammer.Tap({ event: 'doubletap', taps: 2 }) );
// ham.get('doubletap').recognizeWith('singletap');
// ham.get('singletap').requireFailure('doubletap');
//
// ham.on('singletap', function(e) {
//   console.log(e.type);
// });

// ham.add( new Hammer.Swipe({
//   direction: Hammer.DIRECTION_HORIZONTAL,
//   threshold: Math.floor(0.6 * $(window).width()),
//   velocity: 1.0
// }));
//
// ham.get('swipe').recognizeWith('pan');
//
// ham.on('swiperight swipeleft', function (e) {
//   if (e.type == 'swiperight') {
//     nextPage();
//   } else {
//     prevPage();
//   }
// });

// Need to prevent default for mouse pan.
$('#map-frame').on('mousedown', function (e) {
  e.preventDefault();
});

var autoPanTimeConstant = 125;
var autoPanAmplitude = 250;
var startX, startY, startScale;
var startTime, finalDeltaX, finalDeltaY;

ham.on('pinchstart', function(e) {
  startScale = imageScale;
});

ham.on('pinchmove', function(e) {
  zoomMapImage(startScale * e.scale, e.center.x, e.center.y);
});

ham.on('panstart', function(e) {
  startX = imageOffset.x;
  startY = imageOffset.y;
  finalDeltaX = finalDeltaY = 0;  // Cancel any autopan.
});

ham.on('panmove', function(e) {
  if (imageScale > imageScaleMin) {
    panMapImage(startX + e.deltaX, startY + e.deltaY);
  }
});

ham.on('panend pancancel', function(e) {

  // var x = e.center.x, y = e.center.y;
  // var dx = e.deltaX, dy = e.deltaY;
  // var dt = e.deltaTime;
  // var dist = e.distance, ang = e.angle;
  // var vx = e.velocityX, vy = e.velocityY;
  // var v = e.velocity;
  // var scale = e.scale;
  //
  // var str = '' +
  //   ' x/y=' + x + '/' + y +
  //   ' dx/dy=' + dx + '/' + dy +
  //   ' dt=' + dt +
  //   ' dist=' + dist.toFixed(2) +
  //   ' ang=' + ang.toFixed(2) +
  //   ' v=' + v.toFixed(2) +
  //   ' vx/vy=' + vx.toFixed(2) + '/' + vy.toFixed(2) +
  //   ' scale=' + scale.toFixed(3);
  // console.log(e.type + str);

  if (imageScale > imageScaleMin && Math.abs(e.velocity) > 0.1) {

    // Initialize the kinetic autopan.
    startX = imageOffset.x;
    startY = imageOffset.y;
    finalDeltaX = autoPanAmplitude * e.velocityX;
    finalDeltaY = autoPanAmplitude * e.velocityY;
    startTime = Date.now();
    window.requestAnimationFrame(kineticPan);
  }
});

function kineticPan() {

  var elapsed =  startTime - Date.now();
  var delta = 1 - Math.exp(elapsed / autoPanTimeConstant);
  var dx = Math.round(finalDeltaX * delta);
  var dy = Math.round(finalDeltaY * delta);
  // console.log('kineticPan: dx/dy=' + dx + '/' + dy);

  var rem = Math.max(Math.abs(finalDeltaX - dx), Math.abs(finalDeltaY - dy));
  if (rem > 4) {
    panMapImage(startX + dx, startY + dy);
    window.requestAnimationFrame(kineticPan);
  }
}
