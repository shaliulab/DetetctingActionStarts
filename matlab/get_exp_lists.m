% create csv files
% header:
% frame,<behav>,<behav gt>,image
combined = loadAnonymous('/nrs/branson/kwaki/M134C3VGATXChR2_anno/combined.jab');
data_mat = load('/media/drive1/data/hantman/ToneVsLaserData20150717.mat');
gtdata = data_mat.rawdata;
postproc = load('/nrs/branson/kwaki/M134C3VGATXChR2_anno/data.mat');
postproc = postproc.data;

base_dir = '/localhome/kwaki/outputs/test_predict_comp/';

exp2day = regexp(combined.expDirNames,'/M\d+_(\d{8})','tokens','once');
exp2day = [exp2day{:}];
num_exp = numel(combined.labels);
exp_names = regexp(combined.expDirNames,'(M\d+_\w+)', 'tokens', 'once');
exp_names = [exp_names{:}];
labels = {'Lift', 'Handopen', 'Grab', 'Sup', 'Atmouth', 'Chew'};
headers = {'lift', 'hand', 'grab', 'suppinate', 'mouth', 'chew'};


gt_mice = regexp({gtdata.expdir},'(M\d+)_\d+', 'tokens', 'once');
gt_mice = [gt_mice{:}];
gt_days = regexp({gtdata.expdir},'M\d+_(\d+)', 'tokens', 'once');
gt_days = [gt_days{:}];
gt_exps = regexp({gtdata.expdir},'(M\d+_\w+)', 'tokens', 'once');
gt_exps = [gt_exps{:}];

% m134_idx = find(strcmp('M134', gt_mice));
datamat_exps = {};
datamat_days = {};
prev_len = 0;
label_fields = {'Lift_labl_t0sPos', 'Handopen_labl_t0sPos', 'Grab_labl_t0sPos', 'Sup_labl_t0sPos', 'Atmouth_labl_t0sPos', 'Chew_labl_t0sPos'};

w = gausswin(19);


% setup more variables...
postproc_mice = regexp({postproc.exp},'(M\d+)_\d+', 'tokens', 'once');
postproc_mice = [postproc_mice{:}];
postproc_days = regexp({postproc.exp},'M\d+_(\d+)', 'tokens', 'once');
postproc_days = [postproc_days{:}];
postproc_exps = regexp({postproc.exp},'(M\d+_\w+)', 'tokens', 'once');
postproc_exps = [postproc_exps{:}];
postproc_fields = { ...
    'auto_Lift_t0s', 'auto_Handopen_t0s', 'auto_Grab_t0s', ...
    'auto_Sup_t0s', 'auto_Atmouth_t0s', 'auto_Chew_t0s'};

train_exps = {};
for i = length(gt_exps),
    for j = 1:length(label_fields),
        if ~isempty(gtdata(i).(label_fields{j})),
            gt_haslabels = true;
            break;
        end
    end
    if gt_haslabels == false,
        continue
    end

    post_idx = find(strcmp(gt_exps{i}, postproc_exps));
    if ~isempty(post_idx),
        postproc_haslabels = false;
        for j = 1:length(postproc_fields),
            if ~isempty(postproc(i).(postproc_fields{j})),
                postproc_haslabels = true;
                break;
            end
        end
        if postproc_haslabels == true,
            continue
        end
    end

    train_exps{end+1} = gt_exps{i};
end

% for i = 1:length(postproc_exps),
%     % see if there are labels for the post processed data
%     postproc_haslabels = false;
%     for j = 1:length(postproc_fields),
%         if ~isempty(postproc(i).(postproc_fields{j})),
%             postproc_haslabels = true;
%             break;
%         end
%     end

%     % check to see if the bout labeled data has labels. if it does, don't
%     % use these set (trained with gt info).
%     combined_idx = find(strcmp(postproc_exps{i}, exp_names));
%     combined_haslabels = false;
%     if ~isempty(combined.labels(combined_idx).names),
%         for j = 1:length(labels),
%             if any(strcmp(labels{j}, combined.labels(combined_idx).names{1})),
%                 combined_haslabels = true;
%                 break;
%             end
%         end
%         if combined_haslabels == true,
%             continue;
%         end
%     end

%     % check to see if the gt data has any labels
%     gt_idx = find(strcmp(exp_names{i}, gt_exps));
%     gt_haslabels = false;
%     if isempty(gt_idx),
%         % if this experiment isn't in the gt data, continue.
%         continue;
%     end
%     % if it is, see if the label fields has anything.
%     for j = 1:length(label_fields),
%         if ~isempty(gtdata(gt_idx).(label_fields{j})),
%             gt_haslabels = true;
%             break;
%         end
%     end
%     if gt_haslabels == false,
%         continue
%     end

%     % both have labels, create output space
%     outdir = fullfile(base_dir, exp_names{i});
%     if ~exist(outdir, 'dir')
%         mkdir(outdir);
%     end
%     copy_templates(outdir);
%     % create a symbolic link to the frames
%     system(['ln -s /media/drive1/data/hantman_frames/', exp_names{i}, '/frames ', ...
%             outdir, '/frames']);
    
%     num_frames = postproc(i).trxt1;
%     for j = 1:length(postproc_fields),
%         % get the behavior
%         cvs_data = zeros(num_frames, 2);

%         % apply the predictions
%         cvs_data(postproc(i).(postproc_fields{j}), 1) = 1;
%         % apply the gt data.
%         cvs_data(gtdata(gt_idx).(label_fields{j}), 2) = 1;

%         % filter the data
%         cvs_data = filter(w, 1, cvs_data);

%         outname = fullfile(outdir, ['predict_', headers{j}, '.csv']);
%         cvs_file = fopen(outname, 'w');
%         % write the header
%         fprintf(cvs_file, ['frame,', headers{j}, ',', headers{j}, ' ground truth,image\n']);
%         for k = 1:size(cvs_data, 1),
%             fprintf(cvs_file, '%d,%f,%f,frames/%05d.jpg\n', k, cvs_data(k, 1), cvs_data(k, 2), k);
%         end
%         fclose(cvs_file);
%     end
% end