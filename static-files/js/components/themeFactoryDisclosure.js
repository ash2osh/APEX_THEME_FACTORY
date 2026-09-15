(function () {
    'use strict';
    document.addEventListener('alpine:init', function () {
        Alpine.data('themeFactoryDisclosure', function (itemName) {
            return {
                open: false,
                init: function () {
                    this.open = apex.item(itemName).getValue() === 'Y';
                    this.$watch('open', function (value) {
                        apex.item(itemName).setValue(value ? 'Y' : 'N');
                    });
                },
                toggle: function () { this.open = !this.open; }
            };
        });
    }, { once: true });
}());
