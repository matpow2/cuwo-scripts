$(document).ready(function(){
    var ClassArray = {"1":"Warrior","2":"Ranger","3":"Mage","4":"Rogue"};
    var PlayersArray ={"names":[],"levels":[],"klass":[], "specialz":[], "health":[]};
    var SpecicalizationArray = [["Berserker","Guardian"],["Sniper","Scout"],["Fire","Water"],["Assassin","Ninja"]];
    var ClassCoefArray = [1,3,1.1,1,1.2];
    var reconnection = null;

    function health_calk(scalling, klass, spec, level){
        var max_health = scalling * ClassCoefArray[klass] * Math.pow(2, 3 * (level -1)/(level +19) +1);
        if(spec == "Guardian"){
           max_health = max_health * 1.25;
        }
        return parseInt(max_health);
    }
    function websoc(){
        var socket = new WebSocket("ws://"+window.location.hostname+":"+server_port);

        socket.onopen = function(){
            $('span.reconnecting').text('');
            clearInterval(reconnection);

            socket.send(JSON.stringify({want : 'players'}));

            socket.onmessage = function (event) {
            var sedata = JSON.parse(event.data);
            if(sedata.response == 'players'){

                for(var i= 0; i <  sedata.names.length; i++){
                    if( sedata.names[i] != "undefined"){
                    var j = PlayersArray.names.indexOf(sedata.names[i]);
                    if (j == -1){
                        PlayersArray.names.push(sedata.names[i]);
                        PlayersArray.levels.push(sedata.levels[i]);
                        PlayersArray.klass.push(sedata.klass[i]);
                        var Specialization = SpecicalizationArray[PlayersArray.klass[i]][sedata.specialz[i]];
                        PlayersArray.specialz.push(sedata.specialz[i]);
                        PlayersArray.health.push(health_calk(sedata.health_mult,PlayersArray.klass[i], Specialization, PlayersArray.levels[i]));
                        $('table.players tbody').append("<tr data-name=\"" +PlayersArray.names[i]+"\" ><td class='name'>"+PlayersArray.names[i]+'</td>' +
                            '<td class="level">'+PlayersArray.levels[i]+'</td>' +
                            '<td class="class">'+ClassArray[PlayersArray.klass[i]]+'</td>' +
                            '<td class="specialization">'+Specialization+'</td>' +
                            '<td class="health"><span class="health">' + PlayersArray.health[i] +'</span></td></tr>');
                    }
                    else{
                        PlayersArray.levels[j]=sedata.levels[i];
                        PlayersArray.klass[j]=sedata.klass[i];
                        PlayersArray.specialz[j]=sedata.specialz[i];
                        $("table.players tbody tr[data-name=" +PlayersArray.names[j] + "] td.level").text(PlayersArray.levels[j]);
                        $("table.players tbody tr[data-name=" +PlayersArray.names[j] + "] td.class").text(ClassArray[PlayersArray.klass[i]]);
                        $("table.players tbody tr[data-name=" +PlayersArray.names[j] + "] td.specialization").text(PlayersArray.specialz[j]);
                    }
                }
                }
                //TODO Alert for leaving player
                if(PlayersArray.names.length != 0){
                    for(var i=0; i<PlayersArray.names.length; i++){
                        var j = sedata.names.indexOf(PlayersArray.names[i]);
                        if(j == -1){
                            var deleted = PlayersArray.names.splice(i,1);
                            $("table.players tbody tr[data-name="+ deleted +"]").remove();
                            $("table.players tbody tr.player_controls").remove();
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
                    $(this).after('<tr class="player_controls"><td colspan="4">' +
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
            reconnection = setInterval(function() {websoc()}, 5000);
        };

        window.onunload=function(){socket.close();};
        };
    };
    websoc();
});