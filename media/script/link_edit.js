$(function() {
    var form = $("#linkedit form");
    $("#delete").click(function(ev) {
        if (! form.find('[name=id]').val()) {
            ev.preventDefault();
            return;
        }
        if (confirm('Really delete?')) {
            form.append('<input type="hidden" name="delete" value="delete">');
            form.submit();
        }
    });
    $(".tile").click(function(ev) {
        var tile = $(this), selected = tile.hasClass('selected');
        tile.parent().find('.tile').not(tile).removeClass('selected');
        if (selected) {
            form.find('[name=id]').val('');
            form.find('[type=text]').val('');
            form.find('[type=submit]').val('Add');
        } else {
            form.find('[name=id]').val(tile.attr('id').replace('link-', ''));
            form.find('[name=name]').val(tile.find('.name').html());
            form.find('[name=href]').val(tile.find('.href').html());
            form.find('[name=order]').val(tile.find('.order').html());
            form.find('[type=submit]').val('Update');
        }
        $("#delete").css('display', selected ? 'none' : 'block');
        tile.toggleClass('selected');
    });
});
