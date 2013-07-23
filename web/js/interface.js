$(document).ready(function () {
    var ClassArray = {"1": "Warrior", "2": "Ranger", "3": "Mage", "4": "Rogue"};
    var PlayersArr = {};
    var Specicalizations = [
        ["Berserker", "Guardian"],
        ["Sniper", "Scout"],
        ["Fire", "Water"],
        ["Assassin", "Ninja"]
    ];
    var ClassCoefArray = [1, 3, 1.1, 1, 1.2];
    var reconnection = null;

    function health_calk(klass, spec, level) {
        var max_health = 100 * ClassCoefArray[klass] * Math.pow(2, 3 * (level - 1) / (level + 19) + 1);
        if (spec == "Guardian") {
            max_health = max_health * 1.25;
        }
        return parseInt(max_health);
    }

    function add_player(data, id) {
        PlayersArr[id] = {};
        PlayersArr[id]['name'] = data['name'];
        PlayersArr[id]['level'] = data['level'];
        PlayersArr[id]['klass'] = data['klass'];
        var Specializ = Specicalizations[data['klass']][data['specialz']];
        PlayersArr[id]['specialz'] = Specializ;
        PlayersArr[id]['health'] = health_calk(data['klass'], Specializ, data['level']);
        $('table.players tbody').append("" +
            "<tr data-id=" + id + "><td class='id'>" + id + '</td>' +
            "<td class='name'>" + data['name'] + '</td>' +
            '<td class="level">' + data['level'] + '</td>' +
            '<td class="class">' + ClassArray[data['klass']] + '</td>' +
            '<td class="specialization">' + Specializ + '</td></tr>');
    }

    function delete_player(id) {
        delete PlayersArr[id];
        $("tr[data-id=" + id + "]").remove();
        $("tr.player_controls").remove();
    }

    function update_player(data, id) {
        PlayersArr[id]['name'] = data['name'];
        PlayersArr[id]['level'] = data['level'];
        PlayersArr[id]['klass'] = data['klass'];
        var Specializ = Specicalizations[data['klass']][data['specialz']];
        PlayersArr[id]['specialz'] = Specializ;
        PlayersArr[id]['health'] = health_calk(data['klass'], Specializ, data['level']);
        $("tr[data-id=" + id + "] td.name").text(data['name']);
        $("tr[data-id=" + id + "] td.level").text(data['level']);
        $("tr[data-id=" + id + "] td.class").text(ClassArray[data['klass']]);
        $("tr[data-id=" + id + "] td.specialization").text(Specializ);
    }

    function add_player_chat(id) {
        var name = PlayersArr[id]['name'];
        $('#serverPlayers').append('<p data-id="' + id + '">id#' + id + ' ' + name + '</p>');
    }

    function delete_player_chat(id) {
        $('#serverPlayers p[data-id="' + id + '"]').remove();
    }

    function send_to_chat(message, id) {
        var name;
        if (id == 0) {
            name = "Server";
        }
        else {
            name = PlayersArr[id]['name'];
        }
        $('#chatMessages').append('<p data-id="' + id + '"><span>' + name + '</span>: ' + message + '</p>');
        $("#chatMessages").scrollTop($("#chatMessages")[0].scrollHeight);
        if ($('#chatMessages > p').length > 200) {
            $('#chatMessages').children(":first").remove();
        }
    }

    function websoc() {
        var socket = new WebSocket("ws://" + window.location.hostname + ":" + server_port);

        function commands_buttons() {
            if ($(this).hasClass('chosen_player') == false) {
                var parent = $(this).parent();
                parent.find('tr.chosen_player').next().remove();
                parent.find('tr.chosen_player').children(":first").removeAttr('rowspan');
                parent.find('tr.chosen_player').removeClass('chosen_player');
                $(this).addClass('chosen_player');
                $(':first-child', this).attr("rowspan", 2);
                $(this).after('<tr class="player_controls"><td colspan="4">' +
                    '<button type="button" value="command_kick" class="btn" >Kick</button>' +
                    '<button type="button" value="command_ban" class="btn" >Ban</button>' +
                    '<input type="text" value="" placeholder="Reason" class="text"></td></tr>');
            }
            $('table.players tbody tr.player_controls td button').off('click').on('click', function () {
                socket.send(JSON.stringify({request: $(this).val(),
                    id: $(this).parent().parent().prev().attr('data-id'),
                    reason: $(this).parent().find('input.text').val()}));
            });
        }
        function send_to_server(message){
            socket.send(JSON.stringify({request:"send_message", message: "Server: "+message}));
        }
        socket.onopen = function () {
            $('span.reconnecting').text('');
            clearInterval(reconnection);
            socket.send(JSON.stringify({request: 'auth', key: auth_key }));
            setTimeout(function () {
                socket.send(JSON.stringify({request: 'get_players'}));
            }, 1000);
            socket.onmessage = function (event) {
                var sedata = JSON.parse(event.data);
                //{'response': 'get_players', palyer_id :{'name': '', 'level': '', 'klass': '', 'specialz': ''}}
                if (sedata['response'] == 'get_players') {
                    var ids = Object.keys(sedata);
                    for (var i = 0; i < Object.keys(sedata).length; i++) {
                        if (sedata[ids[i]]['name'] != "undefined" &&
                            sedata[ids[i]] != "get_players") {
                            var j = Object.keys(PlayersArr).indexOf(ids[i]);
                            if (j == -1) {
                                add_player(sedata[ids[i]], ids[i]);
                                add_player_chat(ids[i]);
                            }
                            else {
                                update_player(sedata[ids[i]], ids[i]);
                            }
                        }
                    }
                    ids = Object.keys(PlayersArr);
                    //TODO Alert for leaving player
                    if (Object.keys(PlayersArr).length != 0) {
                        for (var i = 0; i < Object.keys(PlayersArr).length; i++) {
                            var j = Object.keys(sedata).indexOf(Object.keys(PlayersArr)[i]);
                            if (j == -1) {
                                delete_player_chat(ids[i]);
                                delete_player(ids[i]);
                            }
                        }
                    }
                }
                //{'response': 'chat', 'player_id': player_id,'message': message}
                else if (sedata['response'] == 'chat') {
                    var id = sedata['player_id'];
                    var name = PlayersArr[id]['name'];
                    var message = sedata['message'];
                    send_to_chat(message, id);
                }
            };

            $('table.players').hover(
                function () {
                    $('table.players tbody tr').click(commands_buttons);
                },
                function () {
                    var elem = $('table.players tbody tr.chosen_player');
                    elem.removeClass('chosen_player');
                    elem.children(":first").removeAttr('rowspan');
                    elem.next().remove();
                }
            );

            $('#chatInput').off('keypress').on('keypress',function (e) {
                if (e.which == 13) {
                    send_to_chat($(this).val(), 0);
                    send_to_server($(this).val());
                    return false;
                }
            });
            socket.onclose = function () {
                $('span.reconnecting').text('Reconnecting');
                reconnection = setInterval(function () {
                    websoc()
                }, 5000);
            };

            window.onunload = function () {
                socket.close();
            };
        };
    }
    $('ul.nav li').off('click').on('click', function(){
        var target_tab = $(this).attr('data-name');
        $('ul.nav > li.current_tab').removeClass('current_tab');
        $(this).addClass('current_tab');
        $('.content_container > div:not(.hidden_tab)').addClass('hidden_tab');
        $('.content_container > div#'+ target_tab).removeClass('hidden_tab');
    })
    websoc();
});