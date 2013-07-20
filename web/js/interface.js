$(document).ready(function(){
    var ClassArray = {"1":"Warrior","2":"Ranger","3":"Mage","4":"Rogue"};
    var PlayersArray ={"names":[],"levels":[],"klass":[], "specialz":[]};

    function websoc(){
        var socket = new WebSocket("ws://"+window.location.hostname+":"+server_port);

        socket.onopen = function(){
        $('span.reconnecting').text('');

        socket.send(JSON.stringify({want : 'players'}));

        socket.onmessage = function (event) {
            var sedata = JSON.parse(event.data);
            if(sedata.response == 'players'){

                for(var i= 0; i <  sedata.names.length; i++){
                    var j = PlayersArray.names.indexOf(sedata.names[i]);
                    if (j == -1){
                        PlayersArray.names.push(sedata.names[i]);
                        PlayersArray.levels.push(sedata.levels[i]);
                        PlayersArray.klass.push(sedata.klass[i]);
                        PlayersArray.specialz.push(sedata.specialz[i]);
                        $('table.players tbody').append("<tr data-name=\"" +PlayersArray.names[i]+"\" ><td class='name'>"+PlayersArray.names[i]+'</td>' +
                            '<td class="level">'+PlayersArray.levels[i]+'</td>' +
                            '<td class="class">'+ClassArray[PlayersArray.klass[i]]+'</td>' +
                            '<td class="specialization">'+PlayersArray.specialz[i]+'</td></tr>');
                    }
                    else{
                        PlayersArray.names[j]=sedata.names[i];
                        PlayersArray.levels[j]=sedata.levels[i];
                        PlayersArray.klass[j]=sedata.klass[i];
                        PlayersArray.specialz[j]=sedata.specialz[i];
                        $("table.players tbody tr[data-name=" +PlayersArray.names[j]+ "] td.name").text(PlayersArray.names[j]);
                        $("table.players tbody tr[data-name=" +PlayersArray.names[j] + "] td.level").text(PlayersArray.levels[j]);
                        $("table.players tbody tr[data-name=" +PlayersArray.names[j] + "] td.class").text(ClassArray[PlayersArray.klass[i]]);
                        $("table.players tbody tr[data-name=" +PlayersArray.names[j] + "] td.specialization").text(PlayersArray.specialz[j]);
                    }
                }
                //TODO Alert for leaving player
                var deleted =[];
                if(PlayersArray.names.length != 0){
                    for(var i=0;i<PlayersArray.names.length;i++){
                        var j = sedata.names.indexOf(PlayersArray.names[i]);
                        if(j == -1){
                            deleted.push(PlayersArray.names.splice(i,1));
                            $("table.players tbody tr[data-name="+ deleted[0] +"]").remove();
                            $("table.players tbody tr.player_controls").remove();
                            deleted.push(PlayersArray.levels.splice(i,1));
                            deleted.push(PlayersArray.klass.splice(i,1));
                            deleted.push(PlayersArray.specialz.splice(i,1));
                        }
                    }
                }
            }

        };

        $('table.players').hover(
            function(){

            $('table.players tbody tr').click(function(){
                if($(this).hasClass('chosen_player') == false){
                    var parent = $(this).parent();
                    parent.find('tr.chosen_player').next().remove();
                    parent.find('tr.chosen_player').children(":first").removeAttr('rowspan');
                    parent.find('tr.chosen_player').removeClass('chosen_player');
                    $(this).addClass('chosen_player');
                    $(':first-child',this).attr("rowspan", 2);
                    $(this).after('<tr class="player_controls"><td colspan="3">' +
                        '<button type="button" value="Kick" class="btn" >Kick</button>' +
                        '<button type="button" value="Ban" class="btn" >Ban</button>' +
                        '<input type="text" value="" placeholder="Reason" class="text"></td></tr>');
                }
                $('table.players tbody tr.player_controls td button').unbind('click');
                $('table.players tbody tr.player_controls td button').bind('click', function(){
                    socket.send(JSON.stringify({want:$(this).val(),
                        name:$(this).parent().parent().prev().attr('data-name'),
                        reason:$(this).parent().find('input.text').val()}));
                });
            });


        },
            function(){
            var elem = $('table.players tbody tr.chosen_player');
            elem.removeClass('chosen_player').children(":first");
            elem.children(":first").removeAttr('rowspan');
            elem.next().remove();
        });
        socket.onclose = function(){
            $('span.reconnecting').text('Reconnecting');
            setInterval(function() {websoc()}, 5000);
        };

        window.onunload=function(){socket.close();};
        };
    };
    websoc();
});