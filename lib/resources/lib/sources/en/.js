$(function() {
    var $menu = $(".overlapblackbg, .slideLeft");
    var $wsmenucontent = $(".wsmenucontent");
    var openMenu = function() {
        $($menu).removeClass("menuclose").addClass("menuopen")
    };
    var closeMenu = function() {
        $($menu).removeClass("menuopen").addClass("menuclose")
    };
    $("#navToggle").click(function() {
        if ($wsmenucontent.hasClass("menuopen")) {
            $(closeMenu)
        } else {
            $(openMenu)
        }
    });
    $wsmenucontent.click(function() {
        if ($wsmenucontent.hasClass("menuopen")) {
            $(closeMenu)
        }
    });
    $("#navToggle,.overlapblackbg").on(click, function() {
        $(".wsmenucontainer").toggleClass("mrginleft")
    });
    $(".wsmenu-list li").has(".wsmenu-submenu, .wsmenu-submenu-sub, .wsmenu-submenu-sub-sub").prepend("<span class="wsmenu-click"><i class="wsmenu-arrow fa fa-angle-down"></i></span>");
    $(".wsmenu-list li").has(".megamenu").prepend("<span class="wsmenu-click"><i class="wsmenu-arrow fa fa-angle-down"></i></span>");
    $(".wsmenu-mobile").click(function() {
        $(".wsmenu-list").slideToggle("slow")
    });
    $(".wsmenu-click").click(function() {
        $(this).siblings(".wsmenu-submenu").slideToggle("slow");
        $(this).children(".wsmenu-arrow").toggleClass("wsmenu-rotate");
        $(this).siblings(".wsmenu-submenu-sub").slideToggle("slow");
        $(this).siblings(".wsmenu-submenu-sub-sub").slideToggle("slow");
        $(this).siblings(".megamenu").slideToggle("slow");
    });
});
