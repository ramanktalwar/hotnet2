import json
import sys
sys.path.append("../")
# import hotnet2 as hn
import hnio
import matplotlib.pyplot as plt
import random
import argparse
from constants import *
from collections import defaultdict
import os
import shutil

parser = argparse.ArgumentParser(description='List the type of graphs you would like drawn, and specify the files necessary to render them.')

parser.add_argument(
	'--query', 
	help='List which graphs you would like to render--["network", "oncoprint", "loliplot", "textbox"]', 
	nargs='+', choices = ["network", "oncoprint", "loliplot", "textbox"],
	default=["network", "oncoprint", "loliplot", "textbox"])

parser.add_argument('--hotNetOutput',
	help='This should be the path to the .json file that describes the hotnet output', 
	default = '/research/compbio/MutationNetwork/TCGA/THCA/hotnet2/output/2013-08-14/delta_0.000529847053502/results.json')

parser.add_argument('--edgeFile', 
	help='This should be the path to the .json file that describes the edges of the gene networks',
	default = '/data/compbio/datasets/HeatKernels/pagerank/IntHint/binary+complex+hi2012/inthint_edge_list')

parser.add_argument('--transcriptInfo', 
	help='This should be the path to the .json file that describes the transcript information', 
	default = '/gpfs/main/home/bournewu/pan12.json')

parser.add_argument('--sampleToCancer', 
	help='This should be the path to the .txt file that associates each sample with its cancer type', 
	default = 'misc_gene_info/samples.lst')

parser.add_argument('--truncatingGenes', 
	help='This should be the path to the .tsv file that describes the truncating genes', 
	default = 'misc_gene_info/combined_truncating_annotation.tsv')

parser.add_argument('--inactivatingGenes', 
	help='This should be the path to the .tsv file that describes the inactivating genes', 
	default = 'misc_gene_info/inactivating_genes.tsv')

parser.add_argument('--geneInfo', 
	help='You probably do not want this', 
	default = 'misc_gene_info/table_s4.json')

parser.add_argument('--destination', 
	help='The path to the folder where you would like to output', 
	default = '')

parser.add_argument('--folder', 
	help='The name of the folder you would like to create', 
	default = 'output')
args = parser.parse_args()

query = args.query
parsedPath = args.hotNetOutput
parsedEdges = args.edgeFile
parsedTranscripts = args.transcriptInfo
parsedSampleToCancer = args.sampleToCancer
parsedTruncating = args.truncatingGenes
parsedInactivating = args.inactivatingGenes
parsedGeneInfo = args.geneInfo
parsedOutput = args.destination
parsedOutputFolder = args.folder


# load output from HotNet run
# hn_output = json.load(open("run2.json"))
# hn_output = json.load(open("/research/compbio/users/jeldridg/TestFiles/HotNet2_Hint_MutFreq_Output.json"))
# hn_output = json.load(open("hotnet2_results.json"))
# hn_output = json.load(open("/research/compbio/users/jeldridg/ThyroidCancer/results.json"))
hn_output = json.load(open(parsedPath))

# get lists of connected components
components = hn_output["components"]

# calculate their sizes
# sizes = hn.component_sizes(components)

# verify that the calculated sizes match those in the output file (once strings in JSON keys are converted back to ints)
# sizes2 = dict([(int(size), count) for size, count in hn_output["sizes"].iteritems()])
# print "Sizes from output and calculation match (expect True): %s" % (sizes == sizes2)

# get command-line parameters used for the HotNet run
parameters = hn_output["parameters"]

# print out whether this was a classic or directed HotNet run
# runType = "classic" if parameters["classic"] else "directed"
# print "Was run classic or directed? (expect directed): %s" % runType 

# # load the heat scores used for the HotNet run and show them as a histogram 
heat = hnio.load_heat_json(parameters["heat_file"])
# plt.hist(heat.values(), bins=100)
# plt.show()

# get parameters used for heat file generation
heat_parameters = hn_output["heat_parameters"]

# print out the number of samples with SNVs and CNAs
genes = hnio.load_genes(heat_parameters["gene_file"])
samples = hnio.load_samples(heat_parameters["sample_file"])
snvList = hnio.load_snvs(heat_parameters["snv_file"], genes, samples)
cnaList = hnio.load_cnas(heat_parameters["cna_file"], genes, samples)
# print "There were %s samples with SNVs" % (len(snvList))
# print "There were %s samples with CNAs" % (len(cnaList))

# check whether the first two genes in the largest CC interact
edges = hnio.load_ppi_edges(parsedEdges)
index2gene = hnio.load_index(parameters["infmat_index_file"])
gene2index_mapping = {gene: index for index, gene in index2gene.items()}
gene1index = gene2index_mapping[components[0][0]]
gene2index = gene2index_mapping[components[0][1]]
genes_interact = (gene1index, gene2index) in edges or (gene2index, gene1index) in edges
# print "Do the first two genes in the largest CC interact (expect False)? %s" % (genes_interact)

# how about hte first gene and the third gene?
gene3index = gene2index_mapping[components[0][2]]
genes_interact = (gene1index, gene3index) in edges or (gene3index, gene1index) in edges
# print "Do the first and third genes in the largest CC interact (expect True)? %s" % (genes_interact)

important_genes = []
for subnetwork in components:
	important_genes.extend(subnetwork)


# This loads the annotation data
# TAKE IN AS A PARAMETER IN PYTHON SCRIPT
annotation_data = json.load(open(parsedTranscripts))
if "genes" in annotation_data:
	annotation_data = annotation_data["genes"]

# This remembers the association of each sample to every gene that it contains
# sample_dict = {sample: {} for sample in samples}
sample_dict = defaultdict(dict)

# This remembers the association of each gene with every sample that contains it
gene_dict = defaultdict(list)

cancer_dict = {}

# optional
cancer_gene_file = [line.split(" ") for line in open(parsedSampleToCancer)]
for i in range(len(cancer_gene_file)):
	littlelist=cancer_gene_file[i]
	cancer_dict[littlelist[0]]=littlelist[1].replace("\n", "")

truncating_list = []

# To draw in the black dash
def parseTruncatingGenes(mutationList = parsedTruncating):
	mutation_list = [line.split() for line in open(mutationList)]
	for line in mutation_list:
		gene = line[0]
		sampleID = line[1]
		transcript = line[2]
		cancer = line[3]
		mutation_type = line[4]
		locus = line[5]
		biological_info = line[6]
		truncating_list.append(Mutation(sampleID, gene, mutation_type))

parseTruncatingGenes()

# To determine mutation type--i.e. missense or nonsense
def parseInactivatingGenes(mutationList = parsedInactivating):
	mutation_list = [line.split() for line in open(mutationList)]
	mutation_dict = {}
	for line in mutation_list:
		sample_name = line[0]
		mutation_dict[sample_name] = []
		for i in range(1, len(line)):
			mutation_dict[sample_name].append(line[i])
	return mutation_dict

inactivating_genes = parseInactivatingGenes()


def parseMutationList(mutationList, category):
	for mutation in mutationList:
		cur_sample = str(mutation.sample)
		cur_gene = str(mutation.gene)
		inactivating = False
		if cur_sample in inactivating_genes:
			inactivating = (cur_gene in inactivating_genes[cur_sample])
		if cur_gene in important_genes:
			gene_dict[cur_gene].append(cur_sample)
			if cur_gene not in sample_dict[cur_sample]:
				sample_dict[cur_sample][cur_gene] = { 
						"gene": cur_gene,
						"sample": cur_sample,
						"cancer": cancer_dict[cur_sample] if (cur_sample in cancer_dict) else "NA",
						"inactivating": inactivating}
			sample_dict[cur_sample][cur_gene][category] =  mutation.mut_type
		

parseMutationList(truncating_list, "all")
parseMutationList(snvList, "snv")
parseMutationList(cnaList, "cna")

for cur_sample in sample_dict:
	sample_dict[cur_sample] = sample_dict[cur_sample].values()

# Inputs:	return_list: 		a list holding all the dictionaries that
# 								holds the dictionaries representing the 
#								json for each subnetwork
# 			components_list:	the list of list of genes in each subnetwork

# Output:	the return_list with the node and link fields necessary to
# 			generate the subnetworks filled in

def generateNetworkData(return_list, components_list = components):
	# Generating the nodes and links requires 
	# the links index into the respective nodes
	# This keeps track of each node's index
	index_dict = {}	
	for i in range(len(components_list)):
		nodes = []
		links = []
		index = 0
		current_subnetwork = components_list[i]

		for j in range(len(current_subnetwork)):
			gene1 = str(current_subnetwork[j])
			nodes.append({	"gene": gene1, 
							"category": i,
							"heat": heat[0][gene1] if (gene1 in heat[0]) else 0 })
			if (gene1 not in heat[0]):
				print "ERROR: ", gene1, " is missing its heat score"
			index_dict[gene1] = index
			index += 1

		# Having populated the index_dict, we
		# can now generate all the links
		for gene1 in current_subnetwork:
			for gene2 in current_subnetwork:
				if (gene1 in gene2index_mapping and gene2 in gene2index_mapping):
					if ((gene2index_mapping[gene1], gene2index_mapping[gene2]) in edges) or ((gene2index_mapping[gene2], gene2index_mapping[gene1]) in edges):
						links.append({	"source": index_dict[gene1],
										"target": index_dict[gene2],
										"network": "HINT"})
					else:
						links.append({	"source": index_dict[gene1],
										"target": index_dict[gene2],
										"network": ""})
				else:
					print "ERROR: ", gene1, " or ", gene2, " is not in gene2index_mapping"
				# link["present"] =  link_present
				

		return_list[i]["nodes"] = nodes;
		return_list[i]["links"] = links;

	return return_list

# Inputs:	return_list: 		a list holding all the dictionaries that
# 								holds the dictionaries representing the 
#								json for each subnetwork
# 			components_list:	the list of list of genes in each subnetwork
#			sample_set:			the set of all samples
#			gene_list:			the set of all genes

# Output:	the return_list with the node and link fields necessary to
# 			generate the subnetworks filled in
def generateOncoprintData(return_list,  components_list = components):

	# Okay, we want to populate a json object that is 
	# {	name:
	# 	cancer:
	#	genes: []}
	# And since they have to be in index order, we start by looping through
	# the components list
	# This is a bit convoluted since we
	# get all the genes first, then we can find the samples
	# So the plan of attack is we find all the genes,
	# then we find all the samples, and then from that
	# list of samples we create each json object

	for i in range(len(components_list)):
		current_subnetwork = components_list[i]
		samples_list = list(set(reduce(lambda a, b: a + b, [gene_dict[x] for x in current_subnetwork])))

		return_samples_list = []
		for sample in samples_list:

			mutation_list = []
			for mutation in sample_dict[sample]:
				if mutation["gene"] in current_subnetwork:
					mutation_list.append(mutation)
			# for gene in current_subnetwork:
			# 	# print gene + " in " + str(current_subnetwork) + " is adding "
			# 	if gene in sample_dict[sample]:
			# 		mutation_list.append(sample_dict[sample][gene])
			if len(mutation_list) > 0:
				return_samples_list.append({"name": sample,
											"cancer": cancer_dict[cur_sample] if (cur_sample in cancer_dict) else "NA",
											"genes": mutation_list})

		return_list[i]["samples"] = return_samples_list
	return return_list

def generateLolliplotData(return_list, components_list = components):

	for i in range(len(components_list)):
		current_subnetwork = components_list[i]
		gene_mutations = []
		for current_gene in current_subnetwork:
			transcripts = []
			if current_gene in annotation_data:
				current_annotation_data = annotation_data[current_gene]
				for transcript_name in current_annotation_data:
					current_transcript = current_annotation_data[transcript_name]
					current_mutations = current_transcript["mutations"]
					mutation_array = []
					for mutation in current_mutations:
						locus = mutation["loc"]
						types = mutation["types"]
						for mutation_type in types:
							current_mutation_type = mutation_type["name"]
							current_samples = mutation_type["samples"]
							for current_sample in current_samples:
								mutation_array.append({	"locus": locus,
														"sample": current_sample,
														"mutation": current_mutation_type ,
														"cancer": mutation_type["cancer"] })


					# sequence = ""
					# if transcript_name in protein_sequence_data:
					# 	sequence = protein_sequence_data[cur_domain]
					transcript = {	"name": transcript_name,
									"gene": current_gene,
									"length": current_transcript["length"],
									"domains": current_transcript["domains"],
									# "sequence": sequence,
									"mutations":mutation_array }
					transcripts.append(transcript)


			gene_mutations.append({	"gene": current_gene, 
									"transcripts": transcripts})
#									"mutations": list_of_mutations})
		return_list[i]["annotations"] = gene_mutations
	return return_list
#		END OF HOTNET CODE. IT'S VISUALIZATION TIME!

def generateTextInfo(return_list, components_list = components):
	text_info_list =  json.load(open(parsedGeneInfo))
	if "subnets" in text_info_list:
		text_info_list = text_info_list["subnets"]
	for text_info in text_info_list:
		cur_id = text_info["id"]
		current_subnet_json = json.load(open("../subnets/" + str(cur_id) + ".json"))
		return_list[cur_id-1]["infobox"] = current_subnet_json
		return_list[cur_id-1]["infobox"]["name"] = text_info["name"] 
	return return_list

return_list = [{"nodes": [], "links": [], "samples": [], "annotations": [], "infobox":[]} for x in range(len(components))]


# query = ["network", "oncoprint", "loliplot", "textbox"]
# query = ["network", "loliplot"]
# query = ["textbox"]

if ("network" in query):
	return_list = generateNetworkData(return_list)

if ("oncoprint" in query):
	return_list = generateOncoprintData(return_list)

if ("loliplot" in query):
	return_list = generateLolliplotData(return_list);

# if ("textbox" in query):
# 	return_list = generateTextInfo(return_list);
# print gene_dict

# for i in range(len(return_list)):

	

# 	if ("network" in query):
# 		return_list = generateNetworkData(return_list)

# 	if ("oncoprint" in query):
# 		return_list = generateOncoprintData(return_list)

# 	if ("loliplot" in query):
# 		return_list = generateLolliplotData(return_list);
# if
# 	 ("textbox" in query):
# 		return_list = generateTextInfo(return_list);
# 	with open('subnetwork' + str(i+1) + '.json', 'w+') as outfile:
# 		json.dump(current_subnetwork, outfile, skipkeys=False, ensure_ascii=True, indent=1 )
os.mkdir(parsedOutput + parsedOutputFolder)
with open(parsedOutput + parsedOutputFolder + '/hotnet_viz_data.json', 'w+') as outfile:
	json.dump(return_list, outfile, skipkeys=False, ensure_ascii=True, indent=1 )

shutil.copy("test.html", parsedOutput + parsedOutputFolder + '/index.html' )
shutil.copy("app.js", parsedOutput + parsedOutputFolder + '/app.js' )
shutil.copy("style.css", parsedOutput + parsedOutputFolder + '/style.css' )