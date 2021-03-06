import numpy as np
import cv2

# Identify pixels above the threshold
# Threshold of RGB > 160 does a nice job of identifying ground pixels only
def color_thresh(img, rgb_thresh=(160, 160, 160)):
    # Create an array of zeros same xy size as img, but single channel
    color_select = np.zeros_like(img[:,:,0])
    # Require that each pixel be above all three threshold values in RGB
    # above_thresh will now contain a boolean array with "True"
    # where threshold was met
    above_thresh = (img[:,:,0] > rgb_thresh[0]) \
                & (img[:,:,1] > rgb_thresh[1]) \
                & (img[:,:,2] > rgb_thresh[2])
    # Index the array of zeros with the boolean array and set to 1
    color_select[above_thresh] = 1
    # Return the binary image
    return color_select

def rock_thresh(img,rgb_thresh=(90,90,50)):
    # Create and array of zeros with same xy size as img , but with just one channel
    color_select = np.zeros_like(img[:,:,0])
    # Having a certain range for yellow of the rock
    # rock_thresh will now have a boolean array with "True" where the pixels
    # fall in the range set for a rock
    rock_thresh = (img[:,:,0] > rgb_thresh[0]) \
                & (img[:,:,1] > rgb_thresh[1]) \
                & (img[:,:,2] < rgb_thresh[2])
    # Index the array of zeros with the boolean array and set to 1 to highlight rock pixels
    color_select[rock_thresh] = 1
    # Return the binary image
    return color_select

def obstacle_thresh(img,rgb_thresh=(160,160,160)):
    # Create an array of zeros with same xy size as img , but with just one channel
    color_select=np.zeros_like(img[:,:,0])
    # Anything that is darker than the navigable terrain is 
    # an obstacle and we  use obst_thresh to have a boolean array
    # with "True" where threshold was met
    obst_thresh = (img[:,:,0] < 160) \
                & (img[:,:,1] < 160) \
                & (img[:,:,2] < 160)
    # Index the array of zeros with the boolean array and set 1 to highlight the surroundings
    color_select[obst_thresh] = 1
    # Return the binary image
    return color_select
   
    # Define a function to convert from image coords to rover coords
def rover_coords(binary_img):
    # Identify nonzero pixels
    ypos, xpos = binary_img.nonzero()
    # Calculate pixel positions with reference to the rover position being at the 
    # center bottom of the image.  
    x_pixel = -(ypos - binary_img.shape[0]).astype(np.float)
    y_pixel = -(xpos - binary_img.shape[1]/2 ).astype(np.float)
    return x_pixel, y_pixel


# Define a function to convert to radial coords in rover space
def to_polar_coords(x_pixel, y_pixel):
    # Convert (x_pixel, y_pixel) to (distance, angle) 
    # in polar coordinates in rover space
    # Calculate distance to each pixel
    dist = np.sqrt(x_pixel**2 + y_pixel**2)
    # Calculate angle away from vertical for each pixel
    angles = np.arctan2(y_pixel, x_pixel)
    return dist, angles

# Define a function to map rover space pixels to world space
def rotate_pix(xpix, ypix, yaw):
    # Convert yaw to radians
    yaw_rad = yaw * np.pi / 180
    xpix_rotated = (xpix * np.cos(yaw_rad)) - (ypix * np.sin(yaw_rad))
                            
    ypix_rotated = (xpix * np.sin(yaw_rad)) + (ypix * np.cos(yaw_rad))
    # Return the result  
    return xpix_rotated, ypix_rotated

def translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale): 
    # Apply a scaling and a translation
    xpix_translated = (xpix_rot / scale) + xpos
    ypix_translated = (ypix_rot / scale) + ypos
    # Return the result  
    return xpix_translated, ypix_translated


# Define a function to apply rotation and translation (and clipping)
# Once you define the two functions above this function should work
def pix_to_world(xpix, ypix, xpos, ypos, yaw, world_size, scale):
    # Apply rotation
    xpix_rot, ypix_rot = rotate_pix(xpix, ypix, yaw)
    # Apply translation
    xpix_tran, ypix_tran = translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale)
    # Perform rotation, translation and clipping all at once
    x_pix_world = np.clip(np.int_(xpix_tran), 0, world_size - 1)
    y_pix_world = np.clip(np.int_(ypix_tran), 0, world_size - 1)
    # Return the result
    return x_pix_world, y_pix_world

# Define a function to perform a perspective transform
def perspect_transform(img, src, dst):
           
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (img.shape[1], img.shape[0]))# keep same size as input image
    
    return warped


# Apply the above functions in succession and update the Rover state accordingly
def perception_step(Rover):
    # Perform perception steps to update Rover()
    # TODO: 
    # NOTE: camera image is coming to you in Rover.img
    img = np.imread(Rover.img)
    # 1) Define source and destination points for perspective transform
    source = np.float32([[14, 140], [301 ,140],[200, 96], [118, 96]])
    dst_size = 5 
    bottom_offset = 6
    destination = np.float32([[image.shape[1]/2 - dst_size, image.shape[0] - bottom_offset],
                  [image.shape[1]/2 + dst_size, image.shape[0] - bottom_offset],
                  [image.shape[1]/2 + dst_size, image.shape[0] - 2*dst_size - bottom_offset], 
                  [image.shape[1]/2 - dst_size, image.shape[0] - 2*dst_size - bottom_offset],
                  ])
    # 2) Apply perspective transform
    warped = perspect_transform(grid_img, source, destination)
    
    # 3) Apply color threshold to identify navigable terrain/obstacles/rock samples
    obs_img = obstacle_thresh(img)
    nav_img = color_thresh(img)
    rock_img = rock_thresh(img)
    
    # 4) Update Rover.vision_image (this will be displayed on left side of screen)
    Rover.vision_image[:,:,0] = obs_img * 255
    Rover.vision_image[:,:,1] = rock_img * 255
    Rover.vision_image[:,:,2] = nav_img * 255

    # 5) Convert map image pixel values to rover-centric coords
    nav_xpix, nav_ypix = rover_coords(nav_img)
    obs_xpix, obs_ypix = rover_coords(obs_img)
    rocks_xpix,rocks_ypix = rover_coords(rock_img)
    
    
    # 6) Convert rover-centric pixel values to world coordinates
       
    scale = dst_size * 2
    xpos, ypos = Rover.pos
    yaw = Rover.yaw
    worldmap_size = Rover.worldmap.shape[0]
    
    
    nav_x_world,nav_y_world = pix_to_world(nav_xpix,nav_ypix,xpos,ypos,yaw,worldmap_size,scale)
    obs_x_world,obs_y_world = pix_to_world(obs_xpix,obs_ypix,xpos,ypos,yaw,worldmap_size,scale)
    rock_x_world,rock_y_world = pix_to_world(rock_xpix,rock_ypix,xpos,ypos,yaw,worldmap_size,scale)
    
        
        
        
        
        
        
        # 7) Update Rover worldmap (to be displayed on right side of screen)
    Rover.worldmap[obs_y_world, obs_x_world, 0] += 1
    Rover.worldmap[rock_y_world, rock_x_world, 1] += 1
    Rover.worldmap[nav_y_world, nav_x_world, 2] += 1

    # 8) Convert rover-centric pixel positions to polar coordinates
    dist,ang = to_polar_coords(nav_xpix,nav_ypix)
    
    # Update Rover pixel distances and angles
    Rover.nav_dists = dist
    Rover.nav_angles = ang
    
    
 
    
    
    return Rover