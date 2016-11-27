/**
 * Created by Charlie on 11/27/2016.
 */

var $target = null;     // current map list item
var page;               // current page
var maplist = true;     // map list is displayed
var zoomed;             // map image is zoomed
var zoom_scale;         // scale factor for map image
var mousedown = false;  // mouse button is down
var moved = 0;          // how far mouse has moved while down
var lastX;              // last mouse x while down
var lastY;              // last mouse y while down

function show_maplist() {
  $("#map-frame").hide();
  $("#map-list").show();
  maplist = true;
}

function show_map() {
  // swap in and display the current map image
  if ($target) {
    $target.find("div.map-images img").eq(page - 1).clone().replaceAll("#map-frame img");
    $("#map-list").hide();
    $("#map-frame img").parent().show();
    zoom_map(0.0, 0, 0);
    maplist = false;
  }
}

function next_map() {
  if ($target) {
    var $item = $target.next(":not([class~='disabled'])");
    if ($item.length) {
      $target.removeClass("active");
      $target = $item.addClass("active");
      page = 1;
      if (maplist)
        show_maplist();
      else
        show_map();
    }
  }
}

function next_page() {
  if ($target) {
    $mapimages = $target.find("div.map-images img");
    if (page == $mapimages.length)
      next_map();
    else {
      page += 1;
      show_map();
    }
  }
}

function prev_map() {
  if ($target) {
    var $item = $target.prev(":not([class~='disabled'])");
    if ($item.length) {
      $target.removeClass("active");
      $target = $item.addClass("active");
      page = $target.find("div.map-images img").length;
      if (maplist) {
        page = 1;
        show_maplist();
      } else {
        page = $target.find("div.map-images img").length;
        show_map();
      }
    }
  }
}

function prev_page() {
  if ($target) {
    if (page == 1)
      prev_map();
    else {
      page -= 1;
      show_map();
    }
  }
}

function setup_frames() {

  // setup frame heights
  var win = $(window).height();
  var pad = 6;
  var nav = $("nav").outerHeight(false) + pad;
  var content = win - nav - pad;
  $("#content-frame").height(content).css("margin-top", nav + 'px');
  $("#map-list").height(content).css("overflow-y", "auto");
  $("#map-frame").height(content).css("overflow", "hidden");
}

function zoom_map(scale, origin_x, origin_y) {

  // Scale the map image holding the origin fixed.
  // Special case where scale == 0.0 is zoom image to 100% height.

  var nat_x, nat_y;             // native image size
  var img_x, img_y;             // scaled image size
  var offset_x, offset_y;       // offset of img/frame in viewport
  var rel_x, rel_y;             // relative position of mouse in image (1.0, 1.0) => lower-right corner
  var scroll_left, scroll_top;  // scroll offset of img in frame

  var $img = $("#map-frame img");
  var $frame = $img.parent();

  // minimum scale is image height == frame height
  var min_scale = $frame.height() / $img[0].naturalHeight;

  if (scale < min_scale) {

    zoom_scale = min_scale;
    zoomed = false;

  } else {

    zoom_scale = scale;
    zoomed = true;
  }

  offset_x = $frame.offset().left;
  offset_y = $frame.offset().top;

  scroll_x = $frame.scrollLeft();
  scroll_y = $frame.scrollTop();

  img_x = $img.outerWidth();
  img_y = $img.outerHeight();

  nat_x = $img[0].naturalWidth;
  nat_y = $img[0].naturalHeight;

  // calculate new image size and scroll positions
  rel_x = (origin_x - offset_x + scroll_x) / img_x;
  rel_y = (origin_y - offset_y + scroll_y) / img_y;

  img_x = Math.round(zoom_scale * nat_x);
  img_y = Math.round(zoom_scale * nat_y);

  scroll_x = Math.round(img_x * rel_x - origin_x + offset_x);
  scroll_y = Math.round(img_y * rel_y - origin_y + offset_y);

  $img.css("width", img_x).css("height", img_y);
  $frame.scrollLeft(scroll_x).scrollTop(scroll_y);

  console.log('zoom scale: ' + zoom_scale);
}

$(document).ready(function(){

  setup_frames();
  if ($("div.flashed-messages").length) {

    // hide map content if there are messages
    $("#map-list").hide();
    $("#map-frame").hide();

  } else {

    // select the first map in the list
    $target = $("#map-list a.map-item:not([class~='disabled'])").first();
    if ($target.length) {
      $target.addClass('active');
      page = 1;
    } else {
      $target = null;
    }
    show_maplist();
  }

  $(window).resize(setup_frames);

  $("#map-list").click(function(e) {

    // get the map list item
    var $item = $(e.target).closest("a.map-item");

    if ($item.length == 0 || $item.hasClass("disabled")) return;
    if ($target) $target.removeClass('active');

    $target = $item.addClass('active');
    page = 1;
    show_map();

    e.preventDefault();
  });

  $("#show-maps").click(function(e) {

    // toggle display of map list/image
    if (maplist)
      show_map();
    else
      show_maplist()

    e.preventDefault();
  });

  $("#next").click(function(e) {

    // next page/map
    if (maplist)
      next_map();
    else
      next_page();

    e.preventDefault();
  });

  $("#prev").click(function(e) {

    // previous page/map
    if ($target) {
      if (maplist)
        prev_map();
      else
        prev_page();
    }

    e.preventDefault();
  });

  $("#map-frame").mousedown(function(e) {

    // start monitoring mouse movements
    lastX = e.clientX;
    lastY = e.clientY;
    mousedown = true;
    moved = 0;

    e.preventDefault();
  });

  $("#map-frame").mouseup(function(e) {

    // mouse up
    mousedown = false;
    if (moved > 10) {

      // moved a too much to trigger zoom

    } else if (!zoomed) {
      zoom_map(0.75, e.clientX, e.clientY);

    } else if (zoom_scale < 1.0) {
      zoom_map(1.0, e.clientX, e.clientY);

    } else {
      zoom_map(0.0, 0, 0);

    }
    e.preventDefault();
  });

  $("#map-frame").mouseleave(function(e) {

    // stop monitoring mouse movements
    mousedown = false;

    e.preventDefault();
  });

  $('#map-frame').bind('mousewheel', function(e){

    var bump = 1.5;
    if (e.originalEvent.wheelDelta / 120 > 0) {
      console.log('scrolling up !');
      zoom_map(zoom_scale * bump, e.clientX, e.clientY);
    } else {
      console.log('scrolling down !');
      zoom_map(zoom_scale / bump, e.clientX, e.clientY);
    }

    e.preventDefault();
  });

  $("#map-frame").mousemove(function(e) {

    // scroll the map image
    var accel = 2;
    var dx = lastX - e.clientX;
    var dy = lastY - e.clientY;
    moved += Math.abs(dx) + Math.abs(dy);
    if (zoomed && mousedown) {
      $("#map-frame").scrollLeft($("#map-frame").scrollLeft() + dx * accel);
      $("#map-frame").scrollTop($("#map-frame").scrollTop() + dy * accel);
      lastX = e.clientX;
      lastY = e.clientY;
    }

    e.preventDefault();
  });

});  /* document ready */

