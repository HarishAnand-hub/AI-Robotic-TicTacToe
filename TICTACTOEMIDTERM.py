"""
TIC-TAC-TOE ROBOT with DOBOT ARM + MINIMAX + OPENCV
FINAL OPTIMIZED VERSION - IMPROVED GRID DETECTION
WITH B1 and B2 BONUSES
"""

import cv2
import numpy as np
import time
import pydobot

def test_cameras_simple():
    """Simple camera test before starting the game"""
    print("\n" + "="*60)
    print("TESTING CAMERAS")
    print("="*60)
    
    print("\nTesting Camera 0 (External)...")
    print("Press 'Q' to move to next camera")
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("[OK] Camera 0 opened!")
        while True:
            ret, frame = cap.read()
            if ret:
                cv2.putText(frame, "Camera 0 - Press Q to continue", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Camera 0", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
        time.sleep(0.5)
        print("\n[OK] Camera 0 works! Starting game...")
        return True
    else:
        print("[ERROR] Camera 0 not available")
        return False

class RoboticTicTacToe:
    def __init__(self, dobot_port="COM11", camera_index=0):
        """Initialize the Tic-Tac-Toe robot system"""
        print("[INIT] Connecting to Dobot...")
        try:
            self.device = pydobot.Dobot(port=dobot_port)
            self.device.speed(150, 150)
            self.device.suck(False)
            time.sleep(0.5)
            print("[OK] Dobot connected!")
        except Exception as e:
            print(f"[ERROR] Failed to connect to Dobot: {e}")
            raise
        
        self.camera_index = camera_index
        
        # Board state
        self.board = np.zeros((3, 3), dtype=int)
        self.EMPTY = 0
        self.HUMAN = 1
        self.ROBOT = 2
        
        # Robot coordinates
        self.safe_z = 80
        self.home_position = [265.0, -50.0, 80.0, 0]
        
        # 9 pickup spots - CORRECTED COORDINATES
        self.pickup_spots = [
            # LEFT SIDE (4 positions) - All at Y = -147
            [270.9, -147, -46.5, 0],
            [291.2, -147, -46.5, 0],
            [310.8, -147, -46.5, 0],
            [327.9, -147, -46.5, 0],
            
            # RIGHT SIDE (5 positions) - All at Y = 40 (moved away from grid)
            [270.9, 40, -46.5, 0],
            [291.2, 40, -46.5, 0],
            [310.8, 40, -46.5, 0],
            [327.9, 40, -46.5, 0],
            [350.0, 40, -46.5, 0],
        ]
        self.current_pickup_index = 0
        
        # 3x3 grid positions - STANDARDIZED Z-VALUES
        self.grid_positions = {
            (0, 0): [251.0, -93.3, -46.5, 0],
            (0, 1): [250.8, -51.9, -46.5, 0],
            (0, 2): [251.9, -13.7, -46.5, 0],
            (1, 0): [289.5, -91.8, -46.5, 0],
            (1, 1): [290.2, -52.6, -46.5, 0],
            (1, 2): [291.2, -15.8, -46.5, 0],
            (2, 0): [326.7, -94.1, -46.5, 0],
            (2, 1): [328.6, -55.6, -46.5, 0],
            (2, 2): [328.6, -17.6, -46.5, 0],
        }
        
        # Color detection (GREEN and YELLOW)
        self.block_green_lower = np.array([40, 50, 50])
        self.block_green_upper = np.array([80, 255, 255])
        self.block_yellow_lower = np.array([20, 100, 100])
        self.block_yellow_upper = np.array([30, 255, 255])
        
        # Winning combinations
        self.winning_combos = [
            [(0,0), (0,1), (0,2)], [(1,0), (1,1), (1,2)], [(2,0), (2,1), (2,2)],
            [(0,0), (1,0), (2,0)], [(0,1), (1,1), (2,1)], [(0,2), (1,2), (2,2)],
            [(0,0), (1,1), (2,2)], [(0,2), (1,1), (2,0)]
        ]
        
        # Game state
        self.scores = {'human': 0, 'robot': 0, 'draws': 0}
        self.last_move_time = 0
        self.move_cooldown = 3.5
        self.whose_turn = self.HUMAN
        self.detection_delay = 3.0
        self.detection_frames = 5
        self.detection_buffer = []
        
        # Grid detection stability
        self.last_grid_corners = None
        self.grid_stable_frames = 0
        self.grid_stability_threshold = 3
        
        self.move_to_safe_position()
    
    def move_to_safe_position(self):
        """Move robot to safe viewing position"""
        try:
            self.device.move_to(self.home_position[0], self.home_position[1], 
                               self.home_position[2], self.home_position[3])
            time.sleep(0.8)
        except Exception as e:
            print(f"[ERROR] Safe position failed: {e}")
    
    def pick_and_place(self, pickup, place):
        """Pick up block and place it on grid"""
        px, py, pz, pr = pickup
        dx, dy, dz, dr = place
        
        try:
            self.move_to_safe_position()
            
            # Pickup
            self.device.move_to(px, py, self.safe_z, pr)
            time.sleep(0.4)
            self.device.move_to(px, py, pz, pr)
            time.sleep(0.3)
            self.device.suck(True)
            time.sleep(1.2)
            self.device.move_to(px, py, self.safe_z, pr)
            time.sleep(0.4)
            
            self.move_to_safe_position()
            
            # Place
            self.device.move_to(dx, dy, self.safe_z, dr)
            time.sleep(0.4)
            self.device.move_to(dx, dy, dz, dr)
            time.sleep(0.3)
            self.device.suck(False)
            time.sleep(1.2)
            self.device.move_to(dx, dy, self.safe_z, dr)
            time.sleep(0.4)
            
            self.move_to_safe_position()
            
        except Exception as e:
            print(f"[ERROR] Pick and place failed: {e}")
            self.device.suck(False)
            self.move_to_safe_position()
            raise
    
    def robot_shake_head_no(self, error_type="occupied"):
        """B2 BONUS: Shake head left-right to indicate error"""
        print("\n" + "="*60)
        if error_type == "multiple_blocks":
            print("[B2 ERROR] Multiple blocks placed at once!")
        elif error_type == "removed_robot_block":
            print("[B2 ERROR] Robot's block was removed/replaced!")
        elif error_type == "not_your_turn":
            print("[B2 ERROR] Not your turn!")
        print("="*60)
        
        try:
            hx, hy, hz, hr = self.home_position
            shake = 40
            
            self.device.move_to(hx, hy, hz, hr)
            time.sleep(0.3)
            self.device.move_to(hx - shake, hy, hz, hr)
            time.sleep(0.4)
            self.device.move_to(hx + shake, hy, hz, hr)
            time.sleep(0.4)
            self.device.move_to(hx - shake, hy, hz, hr)
            time.sleep(0.4)
            self.device.move_to(hx + shake, hy, hz, hr)
            time.sleep(0.4)
            
            self.move_to_safe_position()
            print("[ROBOT] Error acknowledged!")
            print("="*60 + "\n")
        except:
            self.move_to_safe_position()
    
    def robot_place_block(self, row, col):
        """Robot places a block on the grid"""
        print(f"\n[ROBOT] Placing block at ({row},{col})")
        pickup_pos = self.pickup_spots[self.current_pickup_index]
        self.current_pickup_index = (self.current_pickup_index + 1) % len(self.pickup_spots)
        target_pos = self.grid_positions[(row, col)]
        self.pick_and_place(pickup_pos, target_pos)
        time.sleep(self.detection_delay)
    
    def detect_grid(self, frame):
        """IMPROVED: Detect the 3x3 grid on paper with better algorithms"""
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply stronger preprocessing
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        
        # Method 1: Adaptive threshold (most reliable for varying lighting)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 21, 5)
        
        # Clean up with morphological operations
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Sort by area (largest first)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Try to find the best quadrilateral
        best_quad = None
        best_score = 0
        
        for contour in contours[:10]:  # Check top 10 largest contours
            area = cv2.contourArea(contour)
            
            # Filter by area (between 1% and 80% of frame)
            min_area = (w * h) * 0.01
            max_area = (w * h) * 0.80
            
            if area < min_area or area > max_area:
                continue
            
            # Approximate to polygon
            peri = cv2.arcLength(contour, True)
            
            # Try multiple epsilon values
            for epsilon_factor in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]:
                approx = cv2.approxPolyDP(contour, epsilon_factor * peri, True)
                
                if len(approx) == 4:
                    # Check if it's roughly square-shaped
                    x, y, w_rect, h_rect = cv2.boundingRect(approx)
                    aspect_ratio = float(w_rect) / h_rect if h_rect > 0 else 0
                    
                    # Accept aspect ratios between 0.5 and 2.0 (more lenient)
                    if 0.5 < aspect_ratio < 2.0:
                        # Check if convex
                        if cv2.isContourConvex(approx):
                            # Score based on how square it is (closer to 1.0 is better)
                            score = 1.0 - abs(1.0 - aspect_ratio)
                            score *= area  # Prefer larger areas
                            
                            if score > best_score:
                                best_score = score
                                best_quad = approx.reshape(4, 2)
                                print(f"[GRID] Found candidate: Area={area:.0f}, Aspect={aspect_ratio:.2f}, Score={score:.0f}")
        
        if best_quad is not None:
            # Stabilize grid detection
            if self.last_grid_corners is not None:
                # Check if similar to last detection
                diff = np.mean(np.abs(best_quad - self.last_grid_corners))
                if diff < 20:  # Corners haven't moved much
                    self.grid_stable_frames += 1
                else:
                    self.grid_stable_frames = 0
            else:
                self.grid_stable_frames = 0
            
            self.last_grid_corners = best_quad
            
            # Only return if stable for multiple frames
            if self.grid_stable_frames >= self.grid_stability_threshold:
                return best_quad
        else:
            self.last_grid_corners = None
            self.grid_stable_frames = 0
        
        return self.last_grid_corners if self.grid_stable_frames > 0 else None
    
    def order_points(self, pts):
        """Order corner points consistently"""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect
    
    def get_perspective_transform(self, frame, grid_corners):
        """Get top-down view of grid"""
        if grid_corners is None:
            return None
        pts = self.order_points(grid_corners)
        dst = np.array([[0, 0], [449, 0], [449, 449], [0, 449]], dtype="float32")
        M = cv2.getPerspectiveTransform(pts, dst)
        return cv2.warpPerspective(frame, M, (450, 450))
    
    def detect_block_in_cell(self, cell_image):
        """Detect if cell contains a green or yellow block"""
        cell_blurred = cv2.GaussianBlur(cell_image, (5, 5), 0)
        hsv = cv2.cvtColor(cell_blurred, cv2.COLOR_BGR2HSV)
        
        green_mask = cv2.inRange(hsv, self.block_green_lower, self.block_green_upper)
        yellow_mask = cv2.inRange(hsv, self.block_yellow_lower, self.block_yellow_upper)
        combined_mask = cv2.bitwise_or(green_mask, yellow_mask)
        
        kernel = np.ones((5, 5), np.uint8)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        block_pixels = cv2.countNonZero(combined_mask)
        total_pixels = cell_image.shape[0] * cell_image.shape[1]
        
        return "BLOCK_DETECTED" if (block_pixels / total_pixels) > 0.15 else self.EMPTY
    
    def detect_board_state(self, warped_grid):
        """Detect all blocks on the board - ONLY INSIDE THE WARPED GRID"""
        if warped_grid is None:
            return [[self.board[i][j] for j in range(3)] for i in range(3)]
        
        cell_w = warped_grid.shape[1] // 3
        cell_h = warped_grid.shape[0] // 3
        detected = [[0 for _ in range(3)] for _ in range(3)]
        
        for i in range(3):
            for j in range(3):
                cell = warped_grid[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                result = self.detect_block_in_cell(cell)
                
                if result == "BLOCK_DETECTED":
                    detected[i][j] = self.board[i][j] if self.board[i][j] != self.EMPTY else "NEW_BLOCK"
                else:
                    detected[i][j] = self.board[i][j]
        
        return detected
    
    def check_winner(self, board):
        """Check for winner"""
        for combo in self.winning_combos:
            vals = [board[p[0]][p[1]] for p in combo]
            if vals[0] != self.EMPTY and vals[0] == vals[1] == vals[2]:
                return vals[0]
        return None
    
    def is_board_full(self, board):
        """Check if board is full"""
        return not np.any(board == self.EMPTY)
    
    def get_available_moves(self, board):
        """Get list of empty cells"""
        return [(i, j) for i in range(3) for j in range(3) if board[i][j] == self.EMPTY]
    
    def minimax(self, board, depth, is_max, alpha=-float('inf'), beta=float('inf')):
        """Minimax with alpha-beta pruning"""
        winner = self.check_winner(board)
        if winner == self.ROBOT:
            return 10 - depth
        elif winner == self.HUMAN:
            return depth - 10
        elif self.is_board_full(board):
            return 0
        
        if is_max:
            max_eval = -float('inf')
            for move in self.get_available_moves(board):
                board[move[0]][move[1]] = self.ROBOT
                eval_score = self.minimax(board, depth + 1, False, alpha, beta)
                board[move[0]][move[1]] = self.EMPTY
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in self.get_available_moves(board):
                board[move[0]][move[1]] = self.HUMAN
                eval_score = self.minimax(board, depth + 1, True, alpha, beta)
                board[move[0]][move[1]] = self.EMPTY
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval
    
    def get_best_move(self):
        """Get optimal move using Minimax"""
        best_score = -float('inf')
        best_move = None
        for move in self.get_available_moves(self.board):
            self.board[move[0]][move[1]] = self.ROBOT
            score = self.minimax(self.board, 0, False)
            self.board[move[0]][move[1]] = self.EMPTY
            if score > best_score:
                best_score = score
                best_move = move
        return best_move
    
    def visualize_board(self, frame, warped_grid):
        """Draw X and O on grid"""
        if warped_grid is None:
            return frame
        
        cw = warped_grid.shape[1] // 3
        ch = warped_grid.shape[0] // 3
        overlay = warped_grid.copy()
        
        for i in range(1, 3):
            cv2.line(overlay, (i*cw, 0), (i*cw, overlay.shape[0]), (0, 255, 0), 3)
            cv2.line(overlay, (0, i*ch), (overlay.shape[1], i*ch), (0, 255, 0), 3)
        
        for i in range(3):
            for j in range(3):
                cx, cy = j*cw + cw//2, i*ch + ch//2
                if self.board[i][j] == self.HUMAN:
                    cv2.line(overlay, (cx-30, cy-30), (cx+30, cy+30), (255, 0, 0), 5)
                    cv2.line(overlay, (cx+30, cy-30), (cx-30, cy+30), (255, 0, 0), 5)
                elif self.board[i][j] == self.ROBOT:
                    cv2.circle(overlay, (cx, cy), 35, (0, 0, 255), 5)
        return overlay
    
    def print_board_console(self):
        """Print board to console"""
        symbols = {self.EMPTY: '.', self.HUMAN: 'H', self.ROBOT: 'R'}
        print("\nBoard:")
        for i in range(3):
            print("  " + ' | '.join([symbols[self.board[i][j]] for j in range(3)]))
            if i < 2:
                print("  ---------")
    
    def reset_game(self):
        """Reset for new game"""
        self.board = np.zeros((3, 3), dtype=int)
        self.last_move_time = 0
        self.current_pickup_index = 0
        self.whose_turn = self.HUMAN
        self.detection_buffer = []
        self.last_grid_corners = None
        self.grid_stable_frames = 0
        self.device.suck(False)
        time.sleep(0.5)
        self.move_to_safe_position()
    
    def cleanup(self):
        """Cleanup on exit"""
        self.device.suck(False)
        self.move_to_safe_position()

def main():
    print("\n" + "="*60)
    print("TIC-TAC-TOE ROBOT - IMPROVED GRID DETECTION")
    print("="*60)
    
    if not test_cameras_simple():
        return
    
    try:
        game = RoboticTicTacToe(dobot_port="COM11", camera_index=0)
    except:
        print("[ERROR] Failed to initialize")
        return
    
    print("\nGAME RULES:")
    print("- Draw 3x3 grid with BLACK marker on WHITE paper")
    print("- HUMAN: Place GREEN or YELLOW blocks")
    print("- ROBOT: Picks GREEN or YELLOW blocks")
    print("- System tracks ownership by turn order")
    print("\nTIPS FOR BEST DETECTION:")
    print("- Use THICK black marker")
    print("- Draw on WHITE paper")
    print("- Make grid at least 15cm x 15cm")
    print("- Ensure good lighting")
    print("\nControls: 'R' = Reset | 'Q' = Quit\n")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        game.cleanup()
        return
    
    # B1 BONUS: Choose first player
    print("="*60)
    print("B1 BONUS: WHO GOES FIRST?")
    print("="*60)
    while True:
        try:
            choice = int(input("\n1 - HUMAN | 2 - ROBOT: "))
            if choice in [1, 2]:
                break
        except:
            pass
    
    if choice == 2:
        print("\n[ROBOT GOES FIRST]")
        move = game.get_best_move()
        if move:
            game.robot_place_block(move[0], move[1])
            game.board[move[0]][move[1]] = game.ROBOT
            game.whose_turn = game.HUMAN
            game.last_move_time = time.time()
    else:
        print("\n[HUMAN GOES FIRST]")
    
    game_active = True
    robot_pending = False
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)
            display = frame.copy()
            corners = game.detect_grid(frame)
            
            if corners is not None:
                cv2.polylines(display, [corners], True, (0, 255, 0), 3)
                cv2.putText(display, "GRID DETECTED", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                warped = game.get_perspective_transform(frame, corners)
                if warped is not None:
                    detected = game.detect_board_state(warped)
                    now = time.time()
                    
                    # HUMAN's turn
                    if game_active and game.whose_turn == game.HUMAN:
                        new_moves = [(i,j) for i in range(3) for j in range(3) 
                                    if game.board[i][j] == game.EMPTY and detected[i][j] == "NEW_BLOCK"]
                        
                        # B2 ERROR: Multiple blocks
                        if len(new_moves) > 1 and now - game.last_move_time > game.move_cooldown:
                            print(f"\n[B2 ERROR] {len(new_moves)} blocks placed!")
                            game.robot_shake_head_no("multiple_blocks")
                            game.last_move_time = now
                            game.detection_buffer = []
                        
                        # Valid: One block
                        elif len(new_moves) == 1:
                            key = new_moves[0]
                            game.detection_buffer.append(key)
                            if len(game.detection_buffer) > game.detection_frames:
                                game.detection_buffer.pop(0)
                            
                            if len(game.detection_buffer) >= game.detection_frames:
                                if all(d == key for d in game.detection_buffer):
                                    if now - game.last_move_time > game.move_cooldown:
                                        i, j = key
                                        print(f"\n[HUMAN] Block at ({i},{j})")
                                        game.detection_buffer = []
                                        game.board[i][j] = game.HUMAN
                                        game.print_board_console()
                                        game.last_move_time = now
                                        
                                        winner = game.check_winner(game.board)
                                        if winner == game.HUMAN:
                                            print("\n[WIN] HUMAN WINS!")
                                            game.scores['human'] += 1
                                            game_active = False
                                        elif game.is_board_full(game.board):
                                            print("\n[DRAW] Tie game!")
                                            game.scores['draws'] += 1
                                            game_active = False
                                        else:
                                            game.whose_turn = game.ROBOT
                                            robot_pending = True
                        else:
                            game.detection_buffer = []
                        
                        # B2 ERROR: Robot block tampered
                        for i in range(3):
                            for j in range(3):
                                if game.board[i][j] == game.ROBOT:
                                    if detected[i][j] in [game.EMPTY, "NEW_BLOCK"]:
                                        if now - game.last_move_time > game.move_cooldown:
                                            print(f"\n[B2 ERROR] Robot block at ({i},{j}) tampered!")
                                            game.robot_shake_head_no("removed_robot_block")
                                            game.last_move_time = now
                                            game.detection_buffer = []
                    
                    # ROBOT's turn - human tries to move
                    elif game_active and game.whose_turn == game.ROBOT and not robot_pending:
                        for i in range(3):
                            for j in range(3):
                                if game.board[i][j] == game.EMPTY and detected[i][j] == "NEW_BLOCK":
                                    if now - game.last_move_time > game.move_cooldown:
                                        print("\n[B2 ERROR] Not your turn!")
                                        game.robot_shake_head_no("not_your_turn")
                                        game.last_move_time = now
                    
                    # Execute robot move
                    if robot_pending and game_active:
                        move = game.get_best_move()
                        if move:
                            game.robot_place_block(move[0], move[1])
                            game.board[move[0]][move[1]] = game.ROBOT
                            game.whose_turn = game.HUMAN
                            game.print_board_console()
                            
                            winner = game.check_winner(game.board)
                            if winner == game.ROBOT:
                                print("\n[WIN] ROBOT WINS!")
                                game.scores['robot'] += 1
                                game_active = False
                            elif game.is_board_full(game.board):
                                print("\n[DRAW] Tie game!")
                                game.scores['draws'] += 1
                                game_active = False
                            
                            robot_pending = False
                            game.last_move_time = time.time()
                    
                    visual = game.visualize_board(display, warped)
                    cv2.imshow("Grid", visual)
            else:
                cv2.putText(display, "NO GRID", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            score = f"H:{game.scores['human']} R:{game.scores['robot']} D:{game.scores['draws']}"
            cv2.putText(display, score, (10, display.shape[0]-20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.imshow("Camera", display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                game.reset_game()
                game_active = True
                robot_pending = False
    
    except KeyboardInterrupt:
        pass
    finally:
        game.cleanup()
        cap.release()
        cv2.destroyAllWindows()
        print(f"\n[FINAL SCORES] H:{game.scores['human']} R:{game.scores['robot']} D:{game.scores['draws']}\n")

if __name__ == "__main__":
    main()