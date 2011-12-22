#!/usr/bin/env python
# File created on 09 Feb 2010
#file make_3d_plots.py

from __future__ import division

__author__ = "Jesse Stombaugh"
__copyright__ = "Copyright 2011, The QIIME Project"
__credits__ = ["Jesse Stombaugh", "Rob Knight", "Micah Hamady", "Dan Knights",
    "Justin Kuczynski", "Antonio Gonzalez Pena"]
__license__ = "GPL"
__version__ = "1.4.0-dev"
__maintainer__ = "Jesse Stombaugh"
__email__ = "jesse.stombaugh@colorado.edu"
__status__ = "Development"
 

from qiime.util import parse_command_line_parameters, get_options_lookup, create_dir
from qiime.util import make_option
from qiime.make_3d_plots import generate_3d_plots, generate_3d_plots_invue
from qiime.parse import parse_coords,group_by_field,group_by_fields
import shutil
import os
from qiime.colors import sample_color_prefs_and_map_data_from_options
from random import choice
from time import strftime
from qiime.util import get_qiime_project_dir
from qiime.make_3d_plots import get_coord,get_map,remove_unmapped_samples, \
                                get_custom_coords, \
                                process_custom_axes, process_coord_filenames, \
                                remove_nans, scale_custom_coords,\
                                validate_coord_files
from qiime.biplots import get_taxa,get_taxa_coords,get_taxa_prevalence,\
    remove_rare_taxa, make_mage_taxa, make_biplot_scores_output
from cogent.util.misc import get_random_directory_name
import numpy as np

options_lookup = get_options_lookup()

#make_3d_plots.py
script_info={}
script_info['brief_description']="""Make 3D PCoA plots"""
script_info['script_description']="""This script automates the construction of 3D plots (kinemage format) from the PCoA output file generated by principal_coordinates.py (e.g. P1 vs. P2 vs. P3, P2 vs. P3 vs. P4, etc., where P1 is the first component)."""
script_info['script_usage']=[]
script_info['script_usage'].append(("""Default Usage:""","""If you just want to use the default output, you can supply the principal coordinates file (i.e., resulting file from principal_coordinates.py) and a user-generated mapping file, where the default coloring will be based on the SampleID as follows:""","""%prog -i beta_div_coords.txt -m Mapping_file.txt"""))
script_info['script_usage'].append(("","""Additionally, the user can supply their mapping file ("-m") and a specific category to color by ("-b") or any combination of categories. When using the -b option, the user can specify the coloring for multiple mapping labels, where each mapping label is separated by a comma, for example: -b 'mapping_column1,mapping_column2'. The user can also combine mapping labels and color by the combined label that is created by inserting an '&&' between the input columns, for example: -b 'mapping_column1&&mapping_column2'.""",""))
script_info['script_usage'].append(("","""If the user would like to color all categories in their metadata mapping file, they can pass 'ALL' to the '-b' option, as follows:""","""%prog -i beta_div_coords.txt -m Mapping_file.txt -b ALL"""))
script_info['script_usage'].append(("","""As an alternative, the user can supply a preferences (prefs) file, using the -p option. The prefs file allows the user to give specific samples their own columns within a given mapping column. This file also allows the user to perform a color gradient, given a specific mapping column.

If the user wants to color by using the prefs file (e.g. prefs.txt), they can use the following code:""","""%prog -i beta_div_coords.txt -m Mapping_file.txt -p prefs.txt
"""))
script_info['script_usage'].append(("""Output Directory:""","""If you want to give an specific output directory (e.g. "3d_plots"), use the following code:""","""%prog -i principal_coordinates-output_file --o 3d_plots/"""))
script_info['script_usage'].append(("""Background Color Example:""","""If the user would like to color the background white they can use the '-k' option as follows:""","""%prog -i beta_div_coords.txt -m Mapping_file.txt -b ALL -k white"""))
script_info['script_usage'].append(("""Jackknifed Principal Coordinates (w/ confidence intervals):""","""If you have created jackknifed PCoA files, you can pass the folder containing those files, instead of a single file.  The user can also specify the opacity of the ellipses around each point "--ellipsoid_opacity", which is a value from 0-1. Currently there are two metrics "--ellipsoid_method" that can be used for generating the ellipsoids, which are 'IQR' and 'sdev'. The user can specify all of these options as follows:""", """%prog -i jackknifed_pcoas/ -m Mapping_file.txt -b \'mapping_column1,mapping_column1&&mapping_column2\' --ellipsoid_opacity=0.5 --ellipsoid_method=IQR"""))
script_info['script_usage'].append(("""Bi-Plots:""","""If the user would like to see which taxa are more prevalent in different areas of the PCoA plot, they can generate Bi-Plots, by passing a principal coordinates file or folder "-i", a mapping file "-m", and a summarized taxa file "-t" from summarize_taxa.py. Can be combined with jacknifed principal coordinates.""", """%prog -i pcoa.txt -m Mapping_file.txt -t otu_table_level3.txt"""))
script_info['output_description']="""By default, the script will plot the first three dimensions in your file. Other combinations can be viewed using the "Views:Choose viewing axes" option in the KiNG viewer (Chen, Davis, & Richardson, 2009), which may require the installation of kinemage software. The first 10 components can be viewed using "Views:Paralled coordinates" option or typing "/". The mouse can be used to modify display parameters, to click and rotate the viewing axes, to select specific points (clicking on a point shows the sample identity in the low left corner), or to select different analyses (upper right window). Although samples are most easily viewed in 2D, the third dimension is indicated by coloring each sample (dot/label) along a gradient corresponding to the depth along the third component (bright colors indicate points close to the viewer)."""
script_info['required_options']=[\
    make_option('-i', '--coord_fname',
        help='Input principal coordinates filepath (i.e.,' +\
        ' resulting file from principal_coordinates.py).  Alternatively,' +\
        ' a directory containing multiple principal coordinates files for' +\
        ' jackknifed PCoA results.',
        type='existing_path'),
    make_option('-m', '--map_fname', dest='map_fname',
        help='Input metadata mapping filepath',
        type='existing_filepath')
    ]
script_info['optional_options']=[\
    make_option('-b', '--colorby', dest='colorby',\
        help='Comma-separated list categories metadata categories' +\
        ' (column headers) ' +\
        'to color by in the plots. The categories must match the name of a ' +\
        'column header in the mapping file exactly. Multiple categories ' +\
        'can be list by comma separating them without spaces. The user can ' +\
        'also combine columns in the mapping file by separating the ' +\
        'categories by "&&" without spaces. [default=color by all]'),
    make_option('-a', '--custom_axes',
        help='This is the category from the metadata mapping file to use as' +\
        ' a custom axis in the plot.  For instance, if there is a pH' +\
        ' category and you would like to see the samples plotted on that' +\
        ' axis instead of PC1, PC2, etc., one can use this option.  It is' +\
        ' also useful for plotting time-series data. Note: if there is any' +\
        ' non-numeric data in the column, it will not be plotted' +\
        ' [default: %default]'),
    make_option('-p', '--prefs_path',
        help='Input user-generated preferences filepath. NOTE: This is a' +\
        ' file with a dictionary containing preferences for the analysis.' +\
        ' [default: %default]',
        type='existing_filepath'),
    make_option('-k', '--background_color',
        help='Background color to use in the plots. [default: %default]',
        default='black',type='choice',choices=['black','white'],),
    make_option('--ellipsoid_smoothness',
        help='Used only when plotting ellipsoids for jackknifed' +\
        ' beta diversity (i.e. using a directory of coord files' +\
        ' instead of a single coord file). Valid choices are 0-3.' +\
        ' A value of 0 produces very coarse "ellipsoids" but is' +\
        ' fast to render. If you encounter a memory' +\
        ' error when generating or displaying the plots, try including' +\
        ' just one metadata column in your plot. If you still have trouble,' +\
        ' reduce the smoothness level to 0. [default: %default]',
        default="1",type="choice",choices=["0","1","2","3"]),
    make_option('--ellipsoid_opacity',
        help='Used only when plotting ellipsoids for jackknifed' +\
        ' beta diversity (i.e. using a directory of coord files' +\
        ' instead of a single coord file). The valid range is between 0-1.' +\
        ' 0 produces completely transparent (invisible) ellipsoids' +\
        ' and 1 produces completely opaque ellipsoids.' +\
        ' [default=%default]', \
        default=0.33,type=float),
    make_option('--ellipsoid_method',
        help='Used only when plotting ellipsoids for jackknifed' +\
        ' beta diversity (i.e. using a directory of coord files' +\
        ' instead of a single coord file). Valid values are "IQR" and' +\
        ' "sdev". [default=%default]',default="IQR",
        type="choice",choices=["IQR","sdev"]),
    make_option('--master_pcoa',
        help='Used only when plotting ellipsoids for jackknifed beta' +\
        ' diversity (i.e. using a directory of coord files' +\
        ' instead of a single coord file). These coordinates will be the' +\
        ' center of each ellipisoid. [default: %default; arbitrarily' +\
        ' chosen PC matrix will define the center point]',default=None,
        type='existing_filepath'),
    #bipot options
    make_option('-t', '--taxa_fname',
        help='Used only when generating BiPlots. Input summarized taxa '+\
        'filepath (i.e., from summarize_taxa.py). '+\
        'Taxa will be plotted with the samples. [default=%default]', 
        default=None,
        type='existing_filepath'),
    make_option('--n_taxa_keep',
        help='Used only when generating BiPlots. This is the number of taxa '+\
        ' to display. Use -1 to display all. [default: %default]',default=10,
        type=int),
    make_option('--biplot_output_file', 
        help='Used only when generating BiPlots. Output coordinates filepath '+\
        ' when generating a biplot. [default: %default]',default=None,
        type='new_filepath'),
    make_option('--output_format',
        help='Output format. If this option is set to invue you will' +\
        ' need to also use the option -b to define which column(s) from the' +\
        ' metadata file the script should use when writing an output file.' +\
        ' [default: %default]', default='king',type='choice',
        choices=['king','invue']),
    # inVUE options
    make_option('-n', '--interpolation_points', type="int", 
        help='Used only when generating inVUE plots. Number of points' +\
        ' between samples for interpolatation. [default: %default]', default=0),
    make_option('--polyhedron_points', type="int", 
        help='Used only when generating inVUE plots. The number of points' +\
        ' to be generated when creating a frame' +\
        ' around the PCoA plots. [default: %default]', default=4),
    make_option('--polyhedron_offset', type="float", 
        help='Used only when generating inVUE plots. The offset to be added' +\
        ' to each point created when using the' +\
        ' --polyhedron_points option. This is only used when' +\
        ' using the invue output_format. [default: %default]', default=1.5),
    # vector analysis options
    make_option('--add_vectors', dest='add_vectors', default=None,
        help='Create vectors based on a column of the mapping file. This.parameter' +\
        ' accepts up to 2 columns: (1) create the vectors, (2) sort them.' +\
        ' If you wanted to group by Species and' +\
        ' order by SampleID you will pass --add_vectors=Species but if you' +\
        ' wanted to group by Species but order by DOB you will pass' +\
        ' --add_vectors=Species,DOB;' +\
        ' this is useful when you use --custom_axes param [default: %default]'),
    make_option('--rms_algorithm', dest='rms_algorithm', default=None,
        help='The algorithm to calculate the RMS, either avg or trajectory;' +\
        ' both algorithms use all the dimensions and weights them using their' +\
        ' percentange explained; return the norm of the created vectors; and their ' +\
        ' confidence using ANOVA. The vectors are created as follows: for' +\
        ' avg it calculates the average at each timepoint (averaging within' +\
        ' a group), then calculates the norm of each point; for trajectory ' +\
        ' calculates the norm from the 1st-2nd, 2nd-3rd, etc. [default: %default]'),
    make_option('--rms_path', dest='rms_path', default='RMS_output.txt',
        help='Name of the file to save the root mean square (RMS) of the vectors' +\
        ' grouped by the column used with the --add_vectors function. Note that' +\
        ' this option only works with --add_vectors. The file is going to be' +\
        ' created inside the output_dir and its name will start with "RMS".' +\
        ' [default: %default]'),
    options_lookup['output_dir'],
]

script_info['option_label']={'coord_fname':'Principal coordinates filepath',
                             'map_fname':'QIIME-formatted mapping filepath',
                             'colorby': 'Colorby category',
                             'prefs_path': 'Preferences filepath',
                             'background_color': 'Background color',
                             'ellipsoid_opacity':'Ellipsoid opacity',
                             'ellipsoid_method':'Ellipsoid method',
                             'ellipsoid_smoothness':'Ellipsoid smoothness',
                             'taxa_fname': 'Summarized Taxa filepath',
                             'n_taxa_keep': '# of taxa to keep',
                             'biplot_output_file':'Output biplot coordinate filepath',
                             'master_pcoa':'Master principal coordinates filepath',
                             'output_dir': 'Output directory',
                             'output_format': 'Output format',
                             'interpolation_points': '# of interpolation points',
                             'polyhedron_points':'# of polyhedron points',
                             'polyhedron_offset':'Polyhedron offset',
                             'custom_axes':'Custom Axis',
                             'add_vectors':'Create vectors based on metadata',
                             'rms_path':'RMS output path calculations',
                             'rms_algorithm':'RMS algorithm'}
script_info['version'] = __version__

def main():
    option_parser, opts, args = parse_command_line_parameters(**script_info)

    prefs, data, background_color, label_color, ball_scale, arrow_colors= \
                            sample_color_prefs_and_map_data_from_options(opts)
                
    if opts.output_format == 'invue':
        # validating the number of points for interpolation
        if (opts.interpolation_points<0):
            option_parser.error('The --interpolation_points should be ' +\
                            'greater or equal to 0.')
                            
        # make sure that coord file has internally consistent # of columns
        coord_files_valid = validate_coord_files(opts.coord_fname)
        if not coord_files_valid:
            option_parser.error('Every line of every coord file must ' +\
                            'have the same number of columns.')
                            
        #Open and get coord data
        data['coord'] = get_coord(opts.coord_fname, opts.ellipsoid_method)
    
        # remove any samples not present in mapping file
        remove_unmapped_samples(data['map'],data['coord'])

        # if no samples overlapped between mapping file and otu table, exit
        if len(data['coord'][0]) == 0:
            print "\nError: OTU table and mapping file had no samples in common\n"
            exit(1)

        if opts.output_dir:
            create_dir(opts.output_dir,False)
            dir_path=opts.output_dir
        else:
            dir_path='./'
        
        filepath=opts.coord_fname
        if os.path.isdir(filepath):
            coord_files = [fname for fname in os.listdir(filepath) if not \
                           fname.startswith('.')]
            filename = os.path.split(coord_files[0])[-1]
        else:
            filename = os.path.split(filepath)[-1]
	
        generate_3d_plots_invue(prefs, data, dir_path, filename, \
            opts.interpolation_points, opts.polyhedron_points, \
            opts.polyhedron_offset)
        
        #finish script
        return

    # Potential conflicts
    if not opts.custom_axes is None and os.path.isdir(opts.coord_fname):
        # can't do averaged pcoa plots _and_ custom axes in the same plot
        option_parser.error("Please supply either custom axes or multiple coordinate \
files, but not both.")
    # check that smoothness is an integer between 0 and 3
    try:
        ellipsoid_smoothness = int(opts.ellipsoid_smoothness)
    except:
        option_parser.error("Please supply an integer ellipsoid smoothness \
value.")
    if ellipsoid_smoothness < 0 or ellipsoid_smoothness > 3:
        option_parser.error("Please supply an ellipsoid smoothness value \
between 0 and 3.")
    # check that opacity is a float between 0 and 1
    try:
        ellipsoid_alpha = float(opts.ellipsoid_opacity)
    except:
        option_parser.error("Please supply a number for ellipsoid opacity.")
    if ellipsoid_alpha < 0 or ellipsoid_alpha > 1:
        option_parser.error("Please supply an ellipsoid opacity value \
between 0 and 1.")
    # check that ellipsoid method is valid
    ellipsoid_methods = ['IQR','sdev']
    if not opts.ellipsoid_method in ellipsoid_methods:
        option_parser.error("Please supply a valid ellipsoid method. \
Valid methods are: " + ', '.join(ellipsoid_methods) + ".")
  
    # gather ellipsoid drawing preferences
    ellipsoid_prefs = {}
    ellipsoid_prefs["smoothness"] = ellipsoid_smoothness
    ellipsoid_prefs["alpha"] = ellipsoid_alpha

    # make sure that coord file has internally consistent # of columns
    coord_files_valid = validate_coord_files(opts.coord_fname)
    if not coord_files_valid:
        option_parser.error('Every line of every coord file must ' +\
                            'have the same number of columns.')

    #Open and get coord data
    data['coord'] = get_coord(opts.coord_fname, opts.ellipsoid_method)
    
    # remove any samples not present in mapping file
    remove_unmapped_samples(data['map'],data['coord'])
    
    # if no samples overlapped between mapping file and otu table, exit
    if len(data['coord'][0]) == 0:
        print "\nError: OTU table and mapping file had no samples in common\n"
        exit(1)

    # process custom axes, if present.
    custom_axes = None
    if opts.custom_axes:	
        custom_axes = process_custom_axes(opts.custom_axes)
        get_custom_coords(custom_axes, data['map'], data['coord'])
        remove_nans(data['coord'])
        scale_custom_coords(custom_axes,data['coord'])

    # process vectors if requeted
    if opts.add_vectors:
        add_vectors={}
        add_vectors['vectors'] = opts.add_vectors.split(',')
        if len(add_vectors)>3:
            raise ValueError, 'You must add maximum 3 columns but %s' % opts.add_vectors
        
        # Validating RMS values
        if opts.rms_algorithm:
            valid_chars = '_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            for c in opts.rms_path:
                if c not in valid_chars:
                    raise ValueError, 'rms_path (%s) has invalid chars' % opts.rms_path
            add_vectors['rms_output'] = {}
            add_vectors['rms_algorithm']=opts.rms_algorithm
            add_vectors['eigvals'] = data['coord'][3]
        else:
            add_vectors['rms_algorithm'] = None
        add_vectors['rms_path'] = opts.rms_path
    else:
    	add_vectors = None

    if opts.taxa_fname != None:
        # get taxonomy counts
        # get list of sample_ids that haven't been removed
        sample_ids = data['coord'][0]
        # get taxa summaries for all sample_ids
        lineages, taxa_counts = get_taxa(opts.taxa_fname, sample_ids)
        data['taxa'] = {}
        data['taxa']['lineages'] = lineages
        data['taxa']['counts'] = taxa_counts

        # get average relative abundance of taxa
        data['taxa']['prevalence'] = get_taxa_prevalence(data['taxa']['counts'])
        remove_rare_taxa(data['taxa'],nkeep=opts.n_taxa_keep)
        # get coordinates of taxa (weighted mean of sample scores)
        data['taxa']['coord'] = get_taxa_coords(data['taxa']['counts'],
            data['coord'][1])
        data['taxa']['coord']

        # write taxa coords if requested
        if not opts.biplot_output_file is None:
            output = make_biplot_scores_output(data['taxa'])            
            fout = open(opts.biplot_output_file,'w')
            fout.write('\n'.join(output))
            fout.close()


    if opts.output_dir:
        create_dir(opts.output_dir,False)
        dir_path=opts.output_dir
    else:
        dir_path='./'
    
    qiime_dir=get_qiime_project_dir()

    jar_path=os.path.join(qiime_dir,'qiime/support_files/jar/')

    data_dir_path = get_random_directory_name(output_dir=dir_path,
                                              return_absolute_path=False)    
    
    try:
        os.mkdir(data_dir_path)
    except OSError:
        pass

    data_file_path=data_dir_path

    jar_dir_path = os.path.join(dir_path,'jar')
    
    try:
        os.mkdir(jar_dir_path)
    except OSError:
        pass
    
    shutil.copyfile(os.path.join(jar_path,'king.jar'), os.path.join(jar_dir_path,'king.jar'))

    filepath=opts.coord_fname
    if os.path.isdir(filepath):
        coord_files = [fname for fname in os.listdir(filepath) if not \
                           fname.startswith('.')]
        filename = os.path.split(coord_files[0])[-1]
    else:
        filename = os.path.split(filepath)[-1]

    try:
        action = generate_3d_plots
    except NameError:
        action = None

    #Place this outside try/except so we don't mask NameError in action
    if action:
        action(prefs,data,custom_axes,background_color,label_color,dir_path, \
                data_file_path,filename,ellipsoid_prefs=ellipsoid_prefs, \
                add_vectors=add_vectors)


if __name__ == "__main__":
    main()
