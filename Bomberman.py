'''
Bomberman AI Competition program

Author: Henry Grover
Created 11/3/16

For Command Line Use:
	C:\Python27\python.exe C:\Users\groveh\Documents\AI_Comp\Bomberman.py

Current goals:
	connect with the server and be able to read board and send message requests
	think about priority - offensive of defensive


	Before trying the game out on the actual matchmaking server, 
	you should definitely try it against our practice bot! All it 
	does is make random moves, and it never drops bombs. Your matches 
	against the practice bot will not affect your matchmaking rating 
	at all. To do this, have your AI send a post request to:

		http://aicomp.io/api/games/practice
	
	with the following information:
	
		{ devkey: your dev key goes here, username: your username goes here }

	This will simulate playing an actual game, and the server will 
	act as normal sending you post responses to your moves in the form 
	of the sample output before whenever it's your turn. You can follow
	the game real-time by going to Games > List Games and finding the
	one that involves your bot. Or, you can simply go to the following
	link to watch:

		http://aicomp.io/games/(game ID)

	To submit a move, send a post request to:

		http://aicomp.io/api/games/submit/(gameID as interpreted from output)

	with data:

		{ devkey: your dev key goes here, playerID: playerID as interpreted from output, move: your move to submit, see legal list below }

	Your AI is not going to get a post response until it's your move again 
	(or if the game ends), so sit back and relax! You've submitted your move. 
'''
import requests
import webbrowser
import math

def open_in_web(gameID):
	url = str('http://aicomp.io/games/'+gameID)
	webbrowser.open_new(url)

def print_board(json,_print):
	_size = json['boardSize']
	player_pos = json['player']['y'],json['player']['x']
	opponent_pos = json['opponent']['y'],json['opponent']['x']
	bomb_map = json['bombMap']
	hard = json['hardBlockBoard']
	soft = json['softBlockBoard']

	board = []
	for x in range(_size):
		x=[]
		for y in range(_size):
			x.append(' ')
		board.append(x)
	line_tracker=-1
	for x in range(len(hard)):
		if(x%_size == 0):
			line_tracker+=1
		
		if(hard[x]==1):
			board[x%_size][line_tracker]='H'
		elif(soft[x]==1):
			board[x%_size][line_tracker]='S'

	for key in bomb_map.keys():
		board[int(key[2])][int(key[0])] = bomb_map[key]['tick']
	board[player_pos[0]][player_pos[1]] = 'P'
	board[opponent_pos[0]][opponent_pos[1]] = 'O'
	global _file
	if(_print):
		_file.write("\n")
		print
		for x in range(_size):
			line=''
			for y in range(_size):
				line+=str(board[x][y])
				line+=' '
			_file.write(line+'\n')
			print line
		


	return board

#checks how far away opponent is
def opponent_distance(player_pos,opponent_pos):
	return measure_dist(player_pos,opponent_pos)

def measure_dist(player_pos,destination):
	x =  abs(player_pos[0]-destination[0])
	y = abs(player_pos[1]-destination[1])
	return math.sqrt(x*x+y*y)

def next_to_hard_block(board,player_pos):
	x,y = player_pos[0],player_pos[1]
	if((x!= 1 and board[x-1][y] == 'H') or (y!=1 and board[x][y-1] == 'H') or (x!= 9 and board[x+1][y] == 'H') or (y!=9 and board[x][y+1] == 'H')):
		return True
	return False
	
#out of all spots on the map with 3 sides soft blocks, 
#	needs: if multiple see which is closer to the middle	
#	needs: compare proportions of blocks left right and up down to see if its a good direction	

#good for quals: badly needs more comparisons to opponent and block proportions
def find_best_bomb_spot_points_priority(board,player_pos,json):
	general_spots = []
	best_bomb_spot = ''
	minimum = 0
	for x in range(len(board)-1):
		for y in range(len(board[x])-1):
			neighbors = count_soft_block_neighbors(board,x,y)
			if(board[x][y] != 'H' and board[x][y] != 'S' and neighbors>=minimum and can_get_to_spot(board,(x,y),player_pos)):
				if(neighbors>minimum):
					minimum = neighbors
					general_spots = []
				general_spots.append((count_soft_block_neighbors(board,x,y),(x,y)))
	if(len(general_spots)>0):
		minimum = 0
		for x in general_spots:
			val = calculate_block_value(len(board),x[1][0],x[1][1])
			if(best_bomb_spot == '' or val>minimum):
				best_bomb_spot = x
				minimum = val
	return best_bomb_spot[1]

#later on add in attention to how many blocks between and pierce
#if opponent is farther than range and theres a hard block next to spot, move over one as long as not on edge of map
#add finishing move and remove the one in decision - check before last series of if statements if the opponent is within your pierce of a spot you can get to and return that spot and plant portal on the way to bomb
def find_best_bomb_spot_aggressive(board,player_pos,opponent_pos,json):
	player_range = json['player']['bombRange']
	minimum = 200
	best_spot = ''
	global _file
	for x in range(len(board)-1):
		for y in range(len(board[x])-1):

			if(((x == opponent_pos[0] and abs(y-opponent_pos[1])<player_range) or (y == opponent_pos[1] and abs(x-opponent_pos[0])<player_range)) and can_get_to_spot(board,(x,y),player_pos)):
				_file.write("\nreturning kill spot opponent within range")
				return (x,y)

			#print measure_dist((x,y),opponent_pos)
			dist = measure_dist((x,y),opponent_pos)
			#print can_escape_bomb(board,player_pos,(x,y),json)
			if(board[x][y] != 'H' and board[x][y] != 'S' and dist<minimum and can_get_to_spot(board,(x,y),player_pos)):
				#print dist
				minimum = dist
				best_spot = (x,y)
	
	_file.write("\nIf we were smart enough to use portals, portal dist: "+str(dist_to_destination_through_portals(board,best_spot,json)))
	x,y = best_spot[0],best_spot[1]
	if(player_range < opponent_distance(player_pos,opponent_pos) and next_to_hard_block(board,best_spot)):
		_file.write("\nChoosing best aggressive spot")
		if (board[x+1][y] == 'H'):
			if(board[x][y+1] != 'S' != 'H'):
				_file.write("\n=======1")
				return best_spot[0],best_spot[1]+1
			if(board[x][y-1] != 'S' != 'H'):
				_file.write("\n=======2")
				return best_spot[0],best_spot[1]-1
		if(board[x+1][y] != 'S' != 'H'):
			_file.write("\n=======3")
			return best_spot[0]+1,best_spot[1]
		if(board[x-1][y] != 'S' != 'H'):
			_file.write("\n=======4")
			return best_spot[0]-1,best_spot[1]
	_file.write("\n=======5")
	return best_spot	


'''
def can_escape_bomb(board,player_pos,bomb,json):
	#print player_pos
	#print travel_path_to(board,(1,1),player_pos)
	 
	if(board[player_pos[0]-2 ][player_pos[1]-1 ]==' ' and can_get_to_spot(board,(player_pos[0]-2,player_pos[1]-1),player_pos)):
		return True
	if(board[player_pos[0]-1 ][player_pos[1]-1 ]==' ' and can_get_to_spot(board,(player_pos[0]-1,player_pos[1]-1),player_pos)):
		return True
	if(board[player_pos[0]-1 ][player_pos[1]-2 ]==' ' and can_get_to_spot(board,(player_pos[0]-1,player_pos[1]-2),player_pos)):
		return True

	if(board[player_pos[0]-2 ][player_pos[1]+1 ]==' ' and can_get_to_spot(board,(player_pos[0]-2,player_pos[1]+1),player_pos)):
		return True
	if(board[player_pos[0]-1 ][player_pos[1]+1 ]==' ' and can_get_to_spot(board,(player_pos[0]-1,player_pos[1]+1),player_pos)):
		return True
	if(board[player_pos[0]-1 ][player_pos[1]+2 ]==' ' and can_get_to_spot(board,(player_pos[0]-1,player_pos[1]+2),player_pos)):
		return True

	if(board[player_pos[0]+1 ][player_pos[1]+1 ]==' ' and can_get_to_spot(board,(player_pos[0]+1,player_pos[1]+1),player_pos)):
		return True
	if(board[player_pos[0]+1 ][player_pos[1]+2 ]==' ' and can_get_to_spot(board,(player_pos[0]+1,player_pos[1]+2),player_pos)):
		return True
	if(board[player_pos[0]+2 ][player_pos[1]+1 ]==' ' and can_get_to_spot(board,(player_pos[0]+2,player_pos[1]+1),player_pos)):
		return True

	if(board[player_pos[0]+1 ][player_pos[1]-1 ]==' ' and can_get_to_spot(board,(player_pos[0]+1,player_pos[1]-1),player_pos)):
		return True
	if(board[player_pos[0]+1 ][player_pos[1]-2 ]==' ' and can_get_to_spot(board,(player_pos[0]+1,player_pos[1]-2),player_pos)):
		return True
	if(board[player_pos[0]+2 ][player_pos[1]-1 ]==' ' and can_get_to_spot(board,(player_pos[0]+2,player_pos[1]-1),player_pos)):
		return True
	

	return False
'''

def measure_travel_dist(board,spot1,spot2):
	global _file
	if(board[spot1[0]][spot1[1]] != ' ' or board[spot2[0]][spot2[1]] != ' ' or can_get_to_spot(board,spot1,spot2) == False):
		return False
	return len(travel_path_to(board,spot1,spot2))

def dist_to_destination_through_portals(board,destination,json):
	x,y = json['player']['y'],json['player']['x']
	orange_portal = json['player']['orangePortal']
	blue_portal   = json['player']['bluePortal']
	global _file

	if(orange_portal!= None):
		orange_portal = orange_portal['y'],orange_portal['x'],orange_portal['direction']
	else:
		_file.write("Returning False 1")
		return False
	
	if(blue_portal != None):
		_file.write("\n"+str(blue_portal))
		if(blue_portal == None):
			_file.write("\nBlue portal is None as a save word")
		if(blue_portal == 'None'):
			_file.write("\nBlue portal is None as string")

		
		print blue_portal
		blue_portal = blue_portal['y'],blue_portal['x'],blue_portal['direction']
	else:
		_file.write("Returning False2")
		return False

	blue_spot = ''
	orange_spot = ''
	#left side of block
	if(orange_portal[2] == 0):
		orange_spot = orange_portal[0], orange_portal[1]-1, 'mr'
	#top of block
	if(orange_portal[2] == 1):
		orange_spot = orange_portal[0]-1, orange_portal[1], 'md'
	#right of block
	if(orange_portal[2] == 2):
		orange_spot = orange_portal[0], orange_portal[1]+1, 'ml'
	#bottom of block
	if(orange_portal[2] == 3):
		orange_spot = orange_portal[0]+1, orange_portal[1], 'mu'
	#left side of block
	if(blue_portal[2] == 0):
		blue_spot = blue_portal[0], blue_portal[1]-1, 'mr'
	#top of block
	if(blue_portal[2] == 1):
		blue_spot = blue_portal[0]-1, blue_portal[1], 'md'
	#right of block
	if(blue_portal[2] == 2):
		blue_spot = blue_portal[0], blue_portal[1]+1, 'ml'
	#bottom of block
	if(blue_portal[2] == 3):
		blue_spot = blue_portal[0]+1, blue_portal[1], 'mu'


	orange_dist = measure_travel_dist(board,(x,y),orange_spot)
	blue_dist = measure_travel_dist(board,(x,y),blue_spot)

	if(orange_dist<blue_dist):
		blue_dist = measure_travel_dist(board,destination,blue_spot)
	elif(blue_dist<orange_dist):
		orange_dist = measure_travel_dist(board,destination,orange_spot)


	if(orange_dist != False and blue_dist != False):
		return orange_dist+blue_dist+1
	_file.write("\nReturning False 3")
	return False




#a last resort - basically useless now that plant_portal_while_moving_to_bomb_drop is implemented 
def portal_escape_bomb_drop(board,move_number,json):

	if(move_number<28):
		return 'b'
	x,y = json['player']['y'],json['player']['x']

	
	# up: all x should have -1
	if(board[x-1][y] == ' '):
		if(board[x-1][y-1] == 'H' or board[x-1][y-1] == 'S'):
			return ['mu','tl','bp','md','b','mu','ml']
		if(board[x-1][y+1] == 'H' or board[x-1][y+1] == 'S'):
			return ['mu','tr','bp','md','b','mu','mr']

	#down: all x should have +1
	if(board[x+1][y] == ' '):
		if(board[x+1][y-1] == 'H' or board[x+1][y-1] == 'S'):
			return ['md','tl','bp','mu','b','md','ml']
		if(board[x+1][y+1] == 'H' or board[x+1][y+1] == 'S'):
			return ['md','tr','bp','mu','b','md','mr']

	#right: all y should have +1
	if(board[x][y+1] == ' '):
		if(board[x+1][y+1] == 'H' or board[x+1][y+1] == 'S'):
			return ['mr','td','bp','ml','b','mr','md']
		if(board[x-1][y+1] == 'H' or board[x-1][y+1] == 'S'):
			return ['mr','tu','bp','ml','b','mr','mu']

	#left: all y should have -1
	if(board[x][y-1] == ' '):
		if(board[x+1][y-1] == 'H' or board[x+1][y-1] == 'S'):
			return ['ml','td','bp','mr','b','ml','md']
		if(board[x-1][y-1] == 'H' or board[x-1][y-1] == 'S'):
			return ['ml','tu','bp','mr','b','ml','mu']

			
	orientation_move = json['player']['orientation']
	if(orientation_move == 0):
		orientation_move = 'ml'
	if(orientation_move == 1):
		orientation_move = 'mu'
	if(orientation_move == 2):
		orientation_move = 'mr'
	if(orientation_move == 3):
		orientation_move = 'md'

	return ['bp','b',orientation_move,'ml']

#should add case where if portals already where it wants to put it skip that step	
def plant_portal_while_moving_to_bomb_drop(board,path,json):
	x,y = json['player']['y'],json['player']['x']
	orange_portal = json['player']['orangePortal']
	blue_portal   = json['player']['bluePortal']

	if(orange_portal=='None'):
		_file.wtite("orange portal equals none")
	
	print orange_portal
	print blue_portal
	global _file
	_file.write("\nORANGE: "+str(orange_portal))
	_file.write("\nBLUE: "+str(blue_portal))

	# move up next so look left and right x,y+-1
	if(path[0] == 'mu'):
		#look left
		if(board[x][y-1] == 'H' or board[x][y-1] == 'S'):
			return ['tl','bp','mu','b','md','ml']
		#look right
		if(board[x][y+1] == 'H' or board[x][y+1] == 'S'):
			return ['tr','bp','mu','b','md','mr']

	# move down next, so look left and right x,y+-1
	if(path[0] == 'md'):
		#look left
		if(board[x][y-1] == 'H' or board[x][y-1] == 'S'):
			return ['tl','bp','md','b','mu','ml']
		#look right
		if(board[x][y+1] == 'H' or board[x][y+1] == 'S'):
			return ['tr','bp','md','b','mu','mr']

	# move right next, so look up and down x+-1,y
	if(path[0] == 'mr'):
		#look up
		if((board[x-1][y] == 'H' or board[x-1][y] == 'S') and (orange_portal['y'] != x-1 or orange_portal['x'] != y)):
			return ['tu','bp','mr','b','ml','mu']
		#look down
		if(board[x+1][y] == 'H' or board[x+1][y] == 'S'):
			return ['td','bp','mr','b','ml','md']

	# move left next, so look up and down x+-1,y
	if(path[0] == 'ml'):
		#look up
		if(board[x-1][y] == 'H' or board[x-1][y] == 'S'):
			return ['tu','bp','ml','b','mr','mu']
		#look down
		if(board[x+1][y] == 'H' or board[x+1][y] == 'S'):
			return ['td','bp','ml','b','mr','md']
	return path


def calculate_block_value(_size,x,y):
	return math.floor((_size-1-x)*x*(_size-1-y)*y*10/((_size-1)^4/16))

def count_soft_block_neighbors(board,x,y):
	count = 0
	for i in range(-1,2):
		for j in range(-1,2):
			if(board[i+x][j+y] == 'S' and (i==0 or j==0) and i!=j):
				count+=1
	return count

def start_new_practice_game():
	initial_post_request = requests.post("http://aicomp.io/api/games/practice",data={ 'devkey' : '581bb810da8dce85358c64c4', 'username' : 'txzbsstte' })
	return initial_post_request.json()

def start_new_matchmaking_game():
	initial_post_request = requests.post("http://aicomp.io/api/games/search",data={ 'devkey' : '581bb810da8dce85358c64c4', 'username' :  'txzbsstte'})
	
#tell the server what move was decided
def submit_move(gameID,playerID,json,move):
	_file.write(' - Submitted move: '+move)
	print "Submitted move:",move
	move_request = requests.post(str("http://aicomp.io/api/games/submit/"+gameID),data={'devkey': '581bb810da8dce85358c64c4','playerID': playerID,'move': move})
	to_return = move_request.json()
	return to_return

def update_positions(json):
	try:
		player_pos = json['player']['y'],json['player']['x']
	except:
		raise Exception("Timed Out")
	opponent_pos = json['opponent']['y'],json['opponent']['x']
	bomb_map = json['bombMap']
	return player_pos,opponent_pos,bomb_map

#takes max of player range and opponent pierce
def safe_from_bomb(board,bomb,_range,player_pos):
	if(player_pos[0]!=bomb[0] and player_pos[1]!=bomb[1]):
		return True
	if((player_pos[0]==bomb[0] or player_pos[1]==bomb[1]) and measure_dist(player_pos,bomb)>_range):
		return True
	return False

def find_closest_safe_spot(board,json):
	bomb_map = json['bombMap']
	player_pos = json['player']['y'],json['player']['x']
	_range = max(int(json['player']['bombRange']),int(json['opponent']['bombRange']))
	

	best_spot = ''
	maximum = 200
	for x in range(len(board)-1):
		for y in range(len(board)-1):
			if(can_get_to_spot(board,(x,y),player_pos)):
				safe_from_all_bombs = True
				for key in bomb_map.keys(): 
					if(safe_from_bomb(board,(int(key[2]),int(key[0])),_range,(x,y))==False):
						safe_from_all_bombs = False
				if(safe_from_all_bombs and measure_dist(player_pos,(x,y))<maximum):
					maximum = measure_dist(player_pos,(x,y))
					best_spot = x,y
	return best_spot

def can_get_to_spot(board,destination,player_pos):
	return can_get_to_spot_helper(board,player_pos[0],player_pos[1],[],destination)

def can_get_to_spot_helper(board,x,y,_prev,destination):
	if(x == destination[0] and y == destination[1]):
		return True
	if(x<0 or x>len(board) or y<0 or y>len(board[x])):
		return False

	_prev.append((x,y))

	if  (((x-1,y) not in _prev) and board[x-1][y] != 'H' and board[x-1][y]!= 'S' and can_get_to_spot_helper(board,x-1,y,_prev,destination)):
		return True
	elif(((x+1,y) not in _prev) and board[x+1][y] != 'H' and board[x+1][y]!= 'S' and can_get_to_spot_helper(board,x+1,y,_prev,destination)):
		return True
	elif(((x,y-1) not in _prev) and board[x][y-1] != 'H' and board[x][y-1]!= 'S' and can_get_to_spot_helper(board,x,y-1,_prev,destination)):
		return True
	elif(((x,y+1) not in _prev) and board[x][y+1] != 'H' and board[x][y+1]!= 'S' and can_get_to_spot_helper(board,x,y+1,_prev,destination)):
		return True
	
	return False

def travel_path_to(board,destination,player_pos):
	#print 'travel path'
	return travel_helper(board,player_pos[0],player_pos[1],[],destination,0)
	
#returns move list 	
def travel_helper(board,x,y,_prev,destination,rec_num):
	rec_num+=1
	events = []
	if(x == destination[0] and y == destination[1]):
		events.append(True)
		return events
	if(x<0 or x>len(board) or y<0 or y>len(board[x])):
		return events
	_prev.append((x,y))
	go_up = []
	go_down = []
	go_left = []
	go_right = []
	char = board[x][y+1]
	if(((x,y+1) not in _prev) and char != 'H' and char!= 'S'):
		go_right = travel_helper(board,x,y+1,_prev,destination,rec_num)
	char = board[x+1][y]
	if(((x+1,y) not in _prev) and char != 'H' and char!= 'S'):
		go_down = travel_helper(board,x+1,y,_prev,destination,rec_num)
	char = board[x][y-1]
	if(((x,y-1) not in _prev) and char != 'H' and char!= 'S'):
		go_left = travel_helper(board,x,y-1,_prev,destination,rec_num)
	char = board[x-1][y]
	if(((x-1,y) not in _prev) and char != 'H' and char!= 'S'):
		go_up = travel_helper(board,x-1,y,_prev,destination,rec_num)
	
	to_append = ''
	best_path = []
	if(len(go_up)>0 and go_up[len(go_up)-1] == True):
		to_append = 'mu'
		best_path = go_up
	if(len(go_down)>0 and go_down[len(go_down)-1] == True):
		if(len(best_path)>0):
			if(len(go_down) < len(best_path)):
				to_append = 'md'
				best_path = go_down
		else:
			to_append = 'md'
			best_path = go_down
	if(len(go_left)>0 and go_left[len(go_left)-1] == True):
		if(len(best_path)>0):
			if(len(go_left) < len(best_path)):
				to_append = 'ml'
				best_path = go_left
		else:
			to_append = 'ml'
			best_path = go_left
	if(len(go_right)>0 and go_right[len(go_right)-1] == True):
		if(len(best_path)>0):
			if(len(go_right) < len(best_path)):
				to_append = 'mr'
				best_path = go_right
		else:
			to_append = 'mr'
			best_path = go_right
	events.append(to_append)
	for x in best_path:
		events.append(x)
	return events

#strategic game start
def play_first_moves(player_pos,opponent_pos,json,gameID,playerID):
	print 'play first moves'
	json = submit_move(gameID,playerID,json, 'md')
	player_pos,opponent_pos,bomb_map = update_positions(json)
	board = print_board(json,True)

	json = submit_move(gameID,playerID,json, 'b')
	player_pos,opponent_pos,bomb_map = update_positions(json)
	board = print_board(json,True)

	json = submit_move(gameID,playerID,json, 'mu')
	player_pos,opponent_pos,bomb_map = update_positions(json)
	board = print_board(json,True)

	json = submit_move(gameID,playerID,json, 'mr')
	player_pos,opponent_pos,bomb_map = update_positions(json)
	board = print_board(json,True)

	json = submit_move(gameID,playerID,json, 'tu')
	player_pos,opponent_pos,bomb_map = update_positions(json)
	board = print_board(json,True)

	json = submit_move(gameID,playerID,json, 'op')
	player_pos,opponent_pos,bomb_map = update_positions(json)
	board = print_board(json,True)

	json = submit_move(gameID,playerID,json, '')
	player_pos,opponent_pos,bomb_map = update_positions(json)
	board = print_board(json,True)

	return player_pos,opponent_pos,json



def next_to_opponent(board,json):
	x,y = json['player']['y'],json['player']['x']
	if(board[x-1][y] == 'O' or board[x+1][y]=='O' or board[x][y-1]=='O' or board[x][y+1]=='O'):
		return True
	return False


def opponent_within_range(board,json):
	player_range = int(json['player']['bombRange'])
	player_pos = json['player']['y'],json['player']['x']
	opponent_pos = json['opponent']['y'],json['opponent']['x']
	global _file

	if(player_pos[0] == opponent_pos[0] and abs(player_pos[1]-opponent_pos[1])<player_range):
		_file.write("returning opponent in range here 1")
		return True
	if(player_pos[1] == opponent_pos[1] and abs(player_pos[0]-opponent_pos[0])<player_range):
		_file.write("returning opponent in range here 2")
		return True
	return False
	

#player has a bomb on the board, and opponent doesnt
#player is out of the way of own bomb
#0 is player, 1 is opponent
#returns a move array
#one bomb at a time for now
def decide(board,move_number,json):
	bomb_map = json['bombMap']
	player_pos = json['player']['y'],json['player']['x']
	opponent_pos = json['opponent']['y'],json['opponent']['x']
	opponent_pierce = int(json['opponent']['bombPierce'])
	player_pierce = int(json['player']['bombPierce'])
	opponent_range = int(json['opponent']['bombRange'])
	player_range = int(json['player']['bombRange'])
	player_bomb_count = int(json['player']['bombCount'])
	player_coins = int(json['player']['coins'])
	opponent_bombs = []
	player_bombs = []

	temp_event_queue = []
	global bomb_on_board
	global _file

	for key in bomb_map.keys():
		if(str(bomb_map[key]['owner']) == '1'):
			opponent_bombs.append( ( int(key[2]),int(key[0]) ) )
		elif(str(bomb_map[key]['owner']) == '0'):
			player_bombs.append( ( int(key[2]),int(key[0]) ) )
	#only one thing to worry about if opponent has bomb on the board, if not safe run
	if(len(opponent_bombs)>0):
		for x in opponent_bombs:
			#if not safe from bomb, run to closest safe spot
			if(safe_from_bomb(board,x,opponent_range,player_pos)==False):
				#print 'run'
				spot = find_closest_safe_spot(board,json)
				return [travel_path_to(board,spot,player_pos)[0]]
	
	#if player has a bomb on the board
	if(len(player_bombs)>0):
		bomb_on_board = True
		#go through bombs and check that player isnt in the way
		for x in player_bombs:
			#if not safe from own bomb, run to closest safe spot
			if(safe_from_bomb(board,x,player_range,player_pos)==False):
				spot = find_closest_safe_spot(board,json)
				_file.write('running')
				print 'running'
				return [travel_path_to(board,spot,player_pos)[0]]
	
		#player is safe, and there is a bomb planted, so upgrade while waiting
		#return a single move
		if(player_coins>0):
			if(player_pierce<opponent_pierce):
				_file.write('buy pierce')
				print 'buy pierce'
				return ['buy_pierce']
			if(player_range<opponent_range or player_range<5):
				_file.write('buy range')
				print 'buy range'
				return ['buy_range']
			if(player_pierce<5):
				_file.write('buy pierce')
				print 'buy pierce'
				return ['buy_pierce']
			if(player_bomb_count == 0):
				_file.write('buy a bomb')
				print 'buy a bomb'
				return ['buy_count']
	
	#decide whether aggressive or neutral

	if(bomb_on_board):
		bomb_on_board = False
		return ['']


	#_____________________________________________________________ Basic  attack
	if(opponent_within_range(board,json)):
		_file.write('\nplant a bomb to kill'+str(plant_portal_while_moving_to_bomb_drop(board,temp_event_queue[:-1],json))+str(move_number))
		print 'plant a bomb to kill',plant_portal_while_moving_to_bomb_drop(board,temp_event_queue[:-1],json)
		return plant_portal_while_moving_to_bomb_drop(board,temp_event_queue[:-1],json)
	



	#________________________________________________________  choose aggressive or non
	reason = ''
	if(player_coins<2 or player_range<4):
		#neutral
		reason = 'coin'
		spot = find_best_bomb_spot_points_priority(board,player_pos,json)
	else:
		#aggressive
		reason = 'aggressive'
		spot = find_best_bomb_spot_aggressive(board,player_pos,opponent_pos,json)
	

	#__________________________________________________________ if at bomb location drop a bomb
	if(spot[0] == player_pos[0] and spot[1] == player_pos[1]):
		if(player_bomb_count>0):
			_file.write('plant a bomb')
			print 'plant a bomb'
			return portal_escape_bomb_drop(board,move_number,json)
		else:
			_file.write('buy a bomb')
			print 'buy a bomb'
			return ['buy_count']
	else:
		#_________________________________________________________ find best spot and return first move
		#not at spot yet, so go there
		print 'heading to best',reason,'bomb spot'
		temp_event_queue = travel_path_to(board,spot,player_pos)
		if(move_number>28 and len(temp_event_queue) == 2):
			_file.write('planting portal on way to bomb'+str(temp_event_queue[:-1]))
			print 'planting portal on way to bomb',temp_event_queue[:-1]
			return plant_portal_while_moving_to_bomb_drop(board,temp_event_queue[:-1],json)
		#print "path from",player_pos,'to',spot,'is',travel_path_to(board,spot,player_pos)

		return [travel_path_to(board,spot,player_pos)[0]]
	

bomb_on_board = False
_file = open('traceback.txt','w+')
_file.write('wrote to file')
					
def play():
	print 'play'
	gameID,playerID = ' ',' '
	
	json = start_new_practice_game()
	#json = start_new_matchmaking_game()

	print json
	gameID,playerID = json['gameID'],json['playerID']
	global _file
	_file.write('\nGameID: '+gameID)
	
	player_pos,opponent_pos,bomb_map = update_positions(json)
	board = print_board(json,True)
	
	player_pos,opponent_pos,json = play_first_moves(player_pos,opponent_pos,json,gameID,playerID)
	
	#open_in_web(gameID)

	
	moves_queue = []
	move_number = 7
	while(json['player']['alive'] and json['opponent']['alive']):
		move_number+=1
		_file.write('\n'+str(move_number))
		if(len(moves_queue) == 0):
			moves_queue = decide(board,move_number,json)
		
		
		else:
			if(moves_queue[0] == ''):
				
				print 'waiting'
			json = submit_move(gameID,playerID,json,moves_queue[0])
			player_pos,opponent_pos,bomb_map = update_positions(json)
			board = print_board(json,True)

			moves_queue = moves_queue[1::]
			
	
	open_in_web(gameID)
	
if __name__ == "__main__":
	
	play()

	
'''

method to find the best spot for a bomb
how to tell what move the opponent made then update it
need a travel with direction priority
	-maybe use an array with vals from -1 to 2 and start at a specific number to set diagonal priority
maybe make safe_from_all_bombs func to make it cleaner

'tl' turn left
'tu' turn up
'tr' turn right
'td' turn down

'' do nothing

'b' drop a bomb - player cant be on a bomb already, and have a bomb credit
				- bomb ticks start from 5 and tick 
buy_range
buy_count
buy_pierce
buy_block

op orange portal
bp blue portal

logic-
	maybe buy either pierce or range or bombs during beginning while waiting 
	for first bomb to detonate 

	check the board for bombs every time and move by dir priority

	two types of moving, dir priority and bomb placement priority

	first few moves hardcoded:
		-set up portals for a getaway, bomb trails, plant bomb at 2,1
		
	should never need to buy bomb points?

	if pierce is larger than dist away, chase player

	if player has a bomb on the board check if every move you make is dangerous

	add something in travel so you dont cross any dangerous blocks while theres an opponent bomb on the map

	efficiently pick directions for travel function, it takes the long route without comparing

	if safe from bomb through portal <----------

Special Cases:
	no soft blocks on the map

	if player cant escape own or opponents range





'''
	
	
	
	
