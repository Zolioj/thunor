import pandas as pd
from datetime import timedelta
from thunor.io import HtsPandas, write_hdf
import os

# The data are 72 hour viability
TIMEPOINT = timedelta(hours=72)
# Assay name (generic luminescence)
ASSAY = 'lum:Lum'
# Conversion factor for well concentrations to molar (from micromolar)
WELL_CONVERSION = 1e-6

COMPOUND_FILE = 'v20.meta.per_compound.txt'
PLATE_FILE = 'v20.meta.per_assay_plate.txt'
CELL_LINE_FILE = 'v20.meta.per_cell_line.txt'
EXPERIMENT_FILE = 'v20.meta.per_experiment.txt'
WELL_FILE = 'v20.data.per_cpd_well.txt'


def _load_compounds(directory):
    compounds = pd.read_csv(
        os.path.join(directory, COMPOUND_FILE),
        sep='\t', index_col='master_cpd_id',
        usecols=['master_cpd_id', 'cpd_name']
    )
    compounds['cpd_name'] = [(d, ) for d in compounds['cpd_name']]
    return compounds


def _load_plates(directory):
    plates = pd.read_csv(
        os.path.join(directory, PLATE_FILE),
        sep='\t', index_col=['assay_plate_barcode'],
        usecols=['experiment_id', 'assay_plate_barcode', 'dmso_plate_avg_log2']
    )
    return plates


def _load_cell_lines(directory):
    cell_lines = pd.read_csv(
        os.path.join(directory, CELL_LINE_FILE),
        sep='\t', index_col='master_ccl_id',
        usecols=['master_ccl_id', 'ccl_name'],
        converters={'ccl_name': str}
    )
    return cell_lines


def _load_experiments(directory):
    experiments = pd.read_csv(
        os.path.join(directory, EXPERIMENT_FILE),
        sep='\t',
        usecols=['experiment_id', 'master_ccl_id']
    )
    # Experiments have multiple runs, but the cell line doesn't change
    experiments = experiments.drop_duplicates()
    experiments = experiments.set_index('experiment_id')
    return experiments


def _load_wells(directory):
    wells = pd.read_csv(
        os.path.join(directory, WELL_FILE),
        sep='\t',
        usecols=['experiment_id', 'assay_plate_barcode', 'raw_value_log2',
                 'cpd_conc_umol', 'master_cpd_id'],
        converters={
            'cpd_conc_umol': float
        }
    )
    # Add a "well number" for each measurement, reserving 0 for control well
    wells['well_num'] = wells.groupby('assay_plate_barcode').cumcount() + 1

    return wells


def import_ctrp(directory):
    print('Reading HTS data...')
    compounds = _load_compounds(directory)
    plates = _load_plates(directory)
    cell_lines = _load_cell_lines(directory)
    experiments = _load_experiments(directory)
    experiments = experiments.merge(cell_lines, left_on='master_ccl_id',
                                    right_index=True)
    wells = _load_wells(directory)
    # num_wells = wells.shape[0]
    wells = wells.merge(experiments, left_on='experiment_id',
                        right_index=True)

    wells = wells.merge(compounds, left_on='master_cpd_id',
                        right_index=True)

    # assert wells.shape[0] == num_wells

    # Process controls (we only have per-plate averages)
    controls_list = []
    for plate in wells['assay_plate_barcode'].unique():
        plate_data = plates.loc[plate]
        cell_line = str(experiments.loc[plate_data['experiment_id']][
                            'ccl_name'])
        controls_list.append({
            'assay': ASSAY,
            'cell_line': cell_line,
            'plate': plate,
            'well_id': '{}__{}'.format(plate, 0),
            'timepoint': TIMEPOINT,
            'value': plate_data['dmso_plate_avg_log2'],
            'well_num': 0
        })
    controls = pd.DataFrame(controls_list)
    controls = controls.set_index(['assay', 'cell_line', 'plate', 'well_id',
                                   'timepoint'])

    # Process doses and assays
    wells = wells.drop(columns=['master_ccl_id', 'master_cpd_id',
                                'experiment_id'])
    wells.columns = ['plate', 'value', 'dose', 'well_num', 'cell_line', 'drug']
    wells['dose'] *= WELL_CONVERSION
    wells['dose'] = [(d, ) for d in wells['dose'].values]
    wells['well_id'] = wells['plate'].astype(str) + '__' + wells[
        'well_num'].astype(str)

    doses = wells.loc[:, ['drug', 'cell_line', 'dose', 'well_id', 'plate',
                          'well_num']]
    doses = doses.set_index(['drug', 'cell_line', 'dose'])

    assays = wells.loc[:, ['well_id', 'value']]
    assays['timepoint'] = TIMEPOINT
    assays['assay'] = ASSAY
    assays = assays.set_index(['assay', 'well_id', 'timepoint'])

    return HtsPandas(doses, assays, controls)


def convert_ctrp(directory='.',
                 output_file='ctrp_v2.h5'):
    hts = import_ctrp(directory)
    print('Writing HDF5 file...')
    write_hdf(hts, output_file)
    print('Done!')
