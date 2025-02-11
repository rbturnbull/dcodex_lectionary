from genericpath import exists
from dcodex.models import Manuscript
from dcodex.similarity import *
from pathlib import Path

from .models import Lectionary, LectionInSystem

def plot_lections_similarity( 
    base_ms, 
    mss_sigla, 
    system = None,
    lections = None,
    min_lection_index = None,            
    max_lection_index = None,            
    output_filename = None,
    csv_filename = None, 
    force_compute = False, 
    gotoh_param = [6.6995597099885345, -0.9209875054657459, -5.097397327423096, -1.3005714416503906], # From PairHMM of whole dataset
    weights = [0.07124444438506426, -0.2723489152810223, -0.634987796501936, -0.05103656566400282], # From whole dataset
    figsize=(12,7),
    colors = ['#007AFF', '#6EC038', 'darkred', 'magenta'],
    mode = LIKELY__UNLIKELY,
    xticks = [],
    xticks_rotation=0,
    minor_markers=1,
    ymin=60,
    ymax=100,
    prior_log_odds=0.0,
    annotations=[],            
    annotation_color='red',
    annotations_spaces_to_lines=False,              
    legend_location="best",
    circle_marker=True,
    highlight_regions=[],
    highlight_color='yellow',
    fill_empty=True,
    space_evenly=False,
    ignore_untranscribed=False,
    yaxis_title=None,
):

    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    rcParams['font.family'] = 'Linux Libertine O'
    rcParams.update({'font.size': 14})

    #plt.rc('text', usetex=True)
    #plt.rc('text.latex', preamble=r'\usepackage{amsmath}')
    

    import matplotlib.ticker as mtick
    import matplotlib.lines as mlines
    from os import access, R_OK
    from os.path import isfile
    from .similarity import similarity_probabilities_df

    from matplotlib.ticker import FixedLocator

    fig, ax = plt.subplots(figsize=figsize)

    mss = [Manuscript.find( siglum ) for siglum in mss_sigla.keys()]

    # Get system if it is not explicitly set
    if system is None:
        if type(base_ms) == Lectionary:
            system = base_ms.system
        else:
            for ms in mss:
                if type(ms) == Lectionary:
                    system = ms.system
                    break
    assert system is not None

    # Calculate Data
    if not force_compute and csv_filename and isfile( csv_filename ) and access(csv_filename, R_OK):
        df = pd.read_csv(csv_filename)
    else:    
        df = similarity_probabilities_df( system, base_ms, mss, weights=weights, gotoh_param=gotoh_param, prior_log_odds=prior_log_odds )
        if csv_filename:
            csv_path = Path(csv_filename)
            csv_path.parent.mkdir(exist_ok=True, parents=True)
            df.to_csv( csv_filename )

    if min_lection_index:
        if isinstance( min_lection_index, LectionInSystem ):
            min_lection_index = min_lection_index.order
        df = df[ df['Lection_Membership__order'] >= min_lection_index ]
    if max_lection_index:
        if isinstance( max_lection_index, LectionInSystem ):
            max_lection_index = max_lection_index.order
        print('max_lection_index', max_lection_index)
        df = df[df['Lection_Membership__order'] <= max_lection_index ]
        
    if lections:
        lection_ids = []
        for lection in lections:
            if isinstance(lection,LectionInSystem):
                lection_ids.append( lection.id )
            else:
                lection_ids.append( lection )
#            print(df)
        df = df[ df['Lection_Membership__id'].isin( lection_ids ) ]
#            print(df)
#            print(lection_ids)
#            return

    min = df.index.min()
    max = df.index.max()
    if fill_empty:
        df = df.set_index( 'Lection_Membership__order' )    
        df = df.reindex( np.arange( min, max+1 ) )  
    
    if space_evenly:
        df.index = np.arange( len(df.index) )

    print(df)
    #return

    circle_marker = 'o' if circle_marker else ''

    for index, ms_siglum in enumerate(mss_sigla.keys()): 
        ms_df = df[ df[ms_siglum+'_similarity'].notnull() ] if ignore_untranscribed else df
        
        
        if mode is HIGHLY_LIKELY__LIKELY__ELSE:
            plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask(ms_df[ms_siglum+"_probability"] < 0.95), '-', color=colors[index], linewidth=2.5, label=mss_sigla[ms_siglum] + " (Highly Likely)" );
            plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask( (ms_df[ms_siglum+"_probability"] > 0.95) | (ms_df[ms_siglum+"_probability"] < 0.5)), '-', color=colors[index], linewidth=1.5, label=mss_sigla[ms_siglum] + " (Likely)" );        
            plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask(ms_df[ms_siglum+"_probability"] > 0.95), '--', color=colors[index], linewidth=0.5, label=mss_sigla[ms_siglum] + " (Unlikely)" );        
    
        elif mode is HIGHLY_LIKELY__ELSE:
            plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask(ms_df[ms_siglum+"_probability"] < 0.95), '-', color=colors[index], linewidth=2.5, label=mss_sigla[ms_siglum] + " (Highly Likely)" );
            plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'], '--', color=colors[index], linewidth=1, label=mss_sigla[ms_siglum] );        
        elif mode is SOLID:
            plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'], marker=circle_marker, linestyle='-', color=colors[index], linewidth=1, label=mss_sigla[ms_siglum], zorder=10, markerfacecolor='white', markeredgecolor=colors[index], markersize=5.0 );        
        else:    
            plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'].mask(ms_df[ms_siglum+"_probability"] < 0.5), marker=circle_marker, linestyle='-', color=colors[index], linewidth=2.5, label=mss_sigla[ms_siglum] + " (Likely)", zorder=11, markersize=8.0,  markerfacecolor=colors[index], markeredgecolor=colors[index]);
            plt.plot(ms_df.index, ms_df[ms_siglum+'_similarity'], marker=circle_marker, linestyle='--', color=colors[index], linewidth=1, label=mss_sigla[ms_siglum] + " (Unlikely)", zorder=10, markerfacecolor='white', markeredgecolor=colors[index], markersize=5.0 );        
#            plt.plot(df.index, df[ms_siglum+'_similarity'].mask(df[ms_siglum+"_probability"] > 0.5), '--', color=colors[index], linewidth=1, label=mss_sigla[ms_siglum] + " (Unlikely)" );        

    plt.ylim([ymin, ymax])
    ax.set_xticklabels([])

    yaxis_title = yaxis_title or f'Similarity with {base_ms.siglum}'
    plt.ylabel(yaxis_title, horizontalalignment='right', y=1.0)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))


    #######################
    ##### Grid lines  #####
    ####################### 

#    first_lection_membership = system.first_lection_in_system()
#    last_lection_membership = system.last_lection_in_system()
        
    ###### Major Grid Lines ######
    major_tick_locations = []    
    major_tick_annotations = []

    for membership in xticks:
        if type(membership) == tuple:
            if not isinstance( membership[0], LectionInSystem ):
                print("Trouble with membership:", membership)
                continue
            print( 'looking for:', membership[0].id, membership )                    
            x = df.index[ df['Lection_Membership__id'] == membership[0].id ].values.item()
            description = membership[-1]
        else:
            if not isinstance( membership, LectionInSystem ):
                print("Trouble with membership:", membership)
                continue
        
            print( 'looking for:', membership.id, membership )
            x = df.index[ df['Lection_Membership__id'] == membership.id ].values.item()
            description = str(membership.day)

        if annotations_spaces_to_lines:
            description = description.replace( ' ', "\n" )
        major_tick_locations.append( x )
        major_tick_annotations.append( description )
        
    plt.xticks(major_tick_locations, major_tick_annotations, rotation=xticks_rotation )        
    linewidth = 2
    ax.xaxis.grid(True, which='major', color='#666666', linestyle='-', alpha=0.4, linewidth=linewidth)
        
    ###### Minor Grid Lines ######
    minor_ticks = [x for x in df.index if x not in major_tick_locations and x % minor_markers == 0]
    ax.xaxis.set_minor_locator(FixedLocator(minor_ticks))
    ax.xaxis.grid(True, which='minor', color='#666666', linestyle='-', alpha=0.2, linewidth=1,)

    ###### Annotations ######
    for annotation in annotations:
        if type(annotation) == tuple:
            if not isinstance( annotation[0], LectionInSystem ):
                print("Trouble with annotation:", annotation)
                continue
        
            annotation_x = df.index[ df['Lection_Membership__id'] == annotation[0].id ].item()
            annotation_description = annotation[-1]
        else:
            if not isinstance( annotation, LectionInSystem ):
                print("Trouble with annotation:", annotation)
                continue
        
            annotation_x = df.index[ df['Lection_Membership__id'] == annotation.id ].item()
            annotation_description = str(annotation.day)            

        if annotations_spaces_to_lines:
            annotation_description = annotation_description.replace( ' ', "\n" )
        plt.axvline(x=annotation_x, color=annotation_color, linestyle="--")
        ax.annotate(annotation_description, xy=(annotation_x, ymax), xycoords='data', ha='center', va='bottom',xytext=(0,10), textcoords='offset points', fontsize=10, family='Linux Libertine O', color=annotation_color)

    ax.legend(shadow=False, title='', framealpha=1, edgecolor='black', loc=legend_location, facecolor="white", ncol=2).set_zorder(100)
    
    for region in highlight_regions:
        from matplotlib.patches import Rectangle
        region_start = region[0]
        if isinstance(region_start, LectionInSystem):
            region_start = df.index[ df['Lection_Membership__id'] == region_start.id ].item()                
        region_end = region[1]
        if isinstance(region_end, LectionInSystem):
            region_end = df.index[ df['Lection_Membership__id'] == region_end.id ].item()                
        
        rect = Rectangle((region_start,ymin),region_end-region_start,ymax-ymin,linewidth=1,facecolor=highlight_color)
        ax.add_patch(rect)


    plt.show()

    if output_filename:
        fig.tight_layout()
        output_path = Path(output_filename)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        fig.savefig(output_filename)    
        
    notnull = False
    for index, ms_siglum in enumerate(mss_sigla.keys()):     
        notnull = notnull | df[ms_siglum+'_similarity'].notnull()
        
    ms_df = df[ notnull ]
    print(ms_df)
            
    for index, ms_siglum in enumerate(mss_sigla.keys()):     
        print( ms_siglum, df[ms_siglum+'_similarity'].mean() )

    print("Number of lections:", ms_df.shape[0])